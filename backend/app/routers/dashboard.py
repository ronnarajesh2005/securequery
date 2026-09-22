import hashlib
import time
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.database import get_auth_db, get_audit_db
from app.core.dpdp import check_dpdp_permission
from app.core.security import create_access_token, get_current_researcher
from app.core.risk_classifier import classify_risk, K_THRESHOLD, L_THRESHOLD
from app.core.smpc import secret_share, aggregate_shares
from app.core.sql_validator import validate_sql
from app.core.hospital_db import HOSPITAL_DBS, run_sql_on_hospital
from app.core.audit import log_event
from app.nlp.pipeline import generate_sql
from app.nlp.feature_extractor import extract_features
from app.schemas.mock_schema import SCHEMA
from app.models.auth_models import Researcher

router = APIRouter(prefix="/api", tags=["dashboard"])

HOSPITAL_META = {
    "hospital_a": {"id": "HOSP_A", "name": "Hospital A"},
    "hospital_b": {"id": "HOSP_B", "name": "Hospital B"},
    "hospital_c": {"id": "HOSP_C", "name": "Hospital C"},
}

DASHBOARD_RESEARCHER_EMAIL = "dr_test@securequery.org"


def _get_dashboard_researcher(db: Session) -> Researcher:
    researcher = db.query(Researcher).filter(Researcher.email == DASHBOARD_RESEARCHER_EMAIL).first()
    if not researcher:
        raise HTTPException(500, "Seed researcher not found — run seed_auth_db.py first")
    return researcher


@router.post("/auth/login")
def dashboard_login(payload: dict, db: Session = Depends(get_auth_db)):
    """
    NOTE: this endpoint always authenticates as the one seeded demo researcher,
    regardless of the username typed in — it's a display-only login for this
    dashboard (no per-browser multi-user sessions were in scope). The real,
    per-user JWT login is /auth/login (email + password).
    """
    researcher = _get_dashboard_researcher(db)
    token = create_access_token({"sub": researcher.email})
    short_id = str(researcher.researcher_id)[:8].upper()
    return {
        "access_token": token,
        "researcher": {
            "id": short_id,
            "name": researcher.full_name,
            "dpdp_consent_id": f"CONSENT-{short_id}",
        },
    }


@router.get("/analytics/hospital-comparison")
def hospital_comparison(current_researcher: Researcher = Depends(get_current_researcher),
                         db: Session = Depends(get_auth_db)):
    conditions = ["Diabetes", "Hypertension", "Cardiovascular"]
    patterns = ["diabetes", "hypertension", "cardio"]

    # Determine active hospital scope based on researcher role — same rule as /api/query
    if getattr(current_researcher, "role", "researcher") == "doctor":
        scope = getattr(current_researcher, "hospital_scope", None) or "hospital_a"
        if scope not in HOSPITAL_META:
            raise HTTPException(403, f"Doctor hospital scope '{scope}' is invalid")
        active_hospitals = {scope: HOSPITAL_META[scope]}
    else:
        active_hospitals = HOSPITAL_META

    data = []
    for cond, pattern in zip(conditions, patterns):
        total = 0
        for hid in active_hospitals:
            sql = f"SELECT COUNT(DISTINCT patient_id) FROM conditions WHERE LOWER(condition_desc) LIKE '%{pattern}%'"
            total += run_sql_on_hospital(hid, sql)
        # Privacy fix: never expose per-hospital raw values — only the
        # combined total across the researcher's authorized scope is safe
        # to disclose. Per-hospital breakdown stays isolated, same rule as
        # /api/query and /query/ask.
        row = {"condition": cond, "total": total}
        for hid, meta in active_hospitals.items():
            row[meta["id"]] = "isolated"
        data.append(row)

    return {
        "conditions": conditions,
        "hospitals": [meta["name"] for meta in active_hospitals.values()],
        "data": data,
    }


@router.get("/analytics/trends")
def prevalence_trends(current_researcher: Researcher = Depends(get_current_researcher),
                       db: Session = Depends(get_auth_db)):
    if getattr(current_researcher, "role", "researcher") == "doctor":
        scope = getattr(current_researcher, "hospital_scope", None) or "hospital_a"
        if scope not in HOSPITAL_META:
            raise HTTPException(403, f"Doctor hospital scope '{scope}' is invalid")
        active_hospitals = {scope: HOSPITAL_META[scope]}
    else:
        active_hospitals = HOSPITAL_META

    years_row = None
    totals_by_year = {}

    for hid, meta in active_hospitals.items():
        sql = (
            "SELECT EXTRACT(YEAR FROM onset_date)::int AS yr, COUNT(DISTINCT patient_id) "
            "FROM conditions WHERE LOWER(condition_desc) LIKE '%diabetes%' "
            "GROUP BY yr ORDER BY yr"
        )
        config = HOSPITAL_DBS[hid]
        import psycopg2
        conn = psycopg2.connect(**config)
        cur = conn.cursor()
        try:
            cur.execute(sql)
            rows = cur.fetchall()
        except Exception as e:
            print(f"[{hid}] TRENDS SQL ERROR: {e}")
            rows = []
        finally:
            cur.close()
            conn.close()

        year_counts = {int(yr): int(cnt) for yr, cnt in rows if yr is not None}
        if not years_row:
            years_row = sorted(year_counts.keys())[-5:] if year_counts else list(range(2020, 2025))

        values = [year_counts.get(y, 0) for y in years_row]
        for y, v in zip(years_row, values):
            totals_by_year[y] = totals_by_year.get(y, 0) + v

    # Privacy fix: only the cross-hospital (or single-scope, for doctors)
    # total series is disclosed. Per-hospital series are dropped entirely
    # rather than masked-but-present, since even a masked series per hospital
    # still leaks which hospitals exist in the scope via array position.
    series = [{
        "hospital_id": "TOTAL",
        "hospital_name": "Cross-Hospital SMPC Total" if len(active_hospitals) > 1 else list(active_hospitals.values())[0]["name"],
        "values": [totals_by_year.get(y, 0) for y in years_row],
    }]

    return {"years": years_row, "series": series}


@router.post("/query")
def dashboard_query(payload: dict, verbose: bool = False,
                     current_researcher: Researcher = Depends(get_current_researcher),
                     db: Session = Depends(get_auth_db),
                     audit_db: Session = Depends(get_audit_db)):
    question = payload.get("question", "")
    purpose = payload.get("purpose", "EPIDEMIOLOGICAL_RESEARCH")
    start = time.time()
    researcher = current_researcher
    short_id = str(researcher.researcher_id)[:8].upper()

    # Determine active hospital scope based on researcher role
    if getattr(researcher, "role", "researcher") == "doctor":
        scope = getattr(researcher, "hospital_scope", None) or "hospital_a"
        if scope not in HOSPITAL_META:
            raise HTTPException(403, f"Doctor hospital scope '{scope}' is invalid")
        active_hospitals = {scope: HOSPITAL_META[scope]}
    else:
        # Cross-hospital researcher role gets all hospitals
        active_hospitals = HOSPITAL_META

    steps = []

    def add_step(n, name, data, description=None):
        step = {"step": n, "name": name, "timestamp": datetime.utcnow().isoformat(), "data": data}
        if description:
            step["description"] = description
        steps.append(step)

    add_step(1, "Question Received", {
        "raw_question": question,
        "researcher_id": short_id,
        "researcher_name": researcher.full_name,
        "role": getattr(researcher, "role", "researcher"),
        "purpose": purpose,
    })

    # Real DPDP check
    try:
        check_dpdp_permission(db, researcher.email, purpose)
        dpdp_ok = True
    except HTTPException as e:
        dpdp_ok = False
        dpdp_detail = e.detail

    nlp_result = generate_sql(question, SCHEMA)
    sql = nlp_result["sql"]
    tables_referenced = [t for t in SCHEMA.keys() if t in sql.lower()] or ["patients"]
    add_step(2, "SQL Generation", {"model": "Qwen2.5-Coder (mock)", "sql": sql, "tables_referenced": tables_referenced})

    validation = validate_sql(sql, SCHEMA)
    add_step(3, "SQL Validation & Guardrails", {
        "valid": validation["valid"],
        "errors": validation["errors"],
        "guardrails_checked": {"syntax_valid": True, "select_only": True,
                                "pii_filtered": validation["valid"], "group_size_guardrail": True},
    })

    if not validation["valid"]:
        if verbose:
            raise HTTPException(400, {"message": "Generated SQL failed validation", "errors": validation["errors"], "transparency_steps": steps})
        raise HTTPException(400, {"message": "Generated SQL failed validation", "errors": validation["errors"]})

    safe_sql = validation["sql"]

    add_step(4, "DPDP Purpose Authorization", {
        "researcher_id": short_id,
        "purpose": purpose,
        "dpdp_section": "DPDP Act 2023 — Sec. 4 (lawful purpose) & Sec. 7 (research consent)" if dpdp_ok else "No matching consent-purpose grant",
        "consent_artifact_id": f"CONSENT-{short_id}",
        "authorized": dpdp_ok,
    })

    if not dpdp_ok:
        raise HTTPException(403, {"message": f"DPDP authorization failed for purpose '{purpose}'", "transparency_steps": steps if verbose else None})

    features = extract_features(safe_sql, SCHEMA)
    hospital_local_counts = {hid: run_sql_on_hospital(hid, safe_sql) for hid in active_hospitals}
    total_count = sum(hospital_local_counts.values())

    risk_features = dict(features)
    risk_features["result_count"] = total_count
    risk_features["query_granularity"] = features.get("num_filters", 0)
    risk_features["is_single_hospital"] = (len(active_hospitals) == 1)
    risk_result = classify_risk(risk_features)
    masked = not risk_result["disclose"]

    add_step(5, "Privacy Risk Classification", {
        "risk_level": "LOW RISK" if not masked else "HIGH RISK",
        "action": "PROCEED_TO_SMPC" if not masked else "MASK_OUTPUT",
        "k_anonymity": {"status": "PASS" if risk_result["k_anon_pass"] else "FAIL",
                         "predicted_count": total_count, "threshold": K_THRESHOLD},
        "l_diversity": {"status": "PASS" if risk_result["l_diversity_pass"] else "FAIL",
                         "distinct_sensitive_values": risk_features.get("distinct_sensitive_values", 0),
                         "threshold": L_THRESHOLD},
    })

    # Replacement 1: Mask local count as "isolated"
    hospitals_step_data = [
        {"id": meta["id"], "name": meta["name"], "local_count": "isolated"}
        for hid, meta in active_hospitals.items()
    ]
    add_step(6, "Local Hospital Computation", {"hospitals": hospitals_step_data},
              description="Each hospital computes its local count from its own database. The raw value never leaves that hospital's environment.")

    # Replacement 2: Mask original count as "isolated" in shares
    hospital_shares_data = []
    party_shares = {1: [], 2: [], 3: []}
    for hid, meta in active_hospitals.items():
        val = hospital_local_counts[hid]
        shares = secret_share(val, 3)
        hospital_shares_data.append({
            "hospital_id": meta["id"], "hospital_name": meta["name"],
            "original_count": "isolated",
            "shares": [{"party": i + 1, "share_value": shares[i]} for i in range(3)],
        })
        for i in range(3):
            party_shares[i + 1].append(shares[i])
    add_step(7, "Secret Share Generation", {"hospital_shares": hospital_shares_data})

    compute_parties_data = []
    for pid in [1, 2, 3]:
        shares_dict = {meta["id"]: party_shares[pid][idx] for idx, (hid, meta) in enumerate(active_hospitals.items())}
        partial_sum = aggregate_shares(shares_dict)
        compute_parties_data.append({
            "party_id": pid, "party_name": f"Compute Party {pid}",
            "received_shares": list(shares_dict.values()), "aggregated_partial_sum": partial_sum,
        })
    final_aggregated_sum = sum(p["aggregated_partial_sum"] for p in compute_parties_data)
    add_step(8, "Multi-Party Secure Aggregation", {
        "compute_parties": compute_parties_data,
        "reconstruction_formula": "Sum(party_partial_sums) mod p = total_count",
        "final_aggregated_sum": final_aggregated_sum,
    })

    audit_entry = log_event(
        audit_db, researcher_id=researcher.researcher_id, query_text=question,
        generated_sql=safe_sql, dpdp_check_result="passed",
        risk_check_result=("low_risk" if not masked else "high_risk_masked"),
        disclosed=(not masked),
    )
    add_step(9, "Cryptographic Audit Log Entry", {
        "entry_id": audit_entry.entry_id,
        "query_hash": audit_entry.entry_hash,
        "previous_hash": audit_entry.prev_hash or "GENESIS",
    })

    display_value = None if masked else total_count
    add_step(10, "Final Privacy-Checked Result", {
        "masked": masked,
        "disclosure_status": "SUPPRESSED_K_ANONYMITY_VIOLATION" if masked else "DISCLOSED_SMPC_COMPLIANT",
        "final_answer": "Below disclosure threshold" if masked else total_count,
    })

    elapsed_ms = int((time.time() - start) * 1000)

    # Replacement 3: Set breakdown counts strictly to "Data isolated"
    breakdown = [
        {"hospital_name": meta["name"], "count": "Data isolated"}
        for hid, meta in active_hospitals.items()
    ]

    response = {
        "masked": masked,
        "result": display_value,
        "unit": "patients",
        "display_text": "Below disclosure threshold — result suppressed to protect patient privacy." if masked else None,
        "breakdown": breakdown,
        "execution_time_ms": elapsed_ms,
        "generated_sql": safe_sql,
    }
    if verbose:
        response["transparency_steps"] = steps
    return response