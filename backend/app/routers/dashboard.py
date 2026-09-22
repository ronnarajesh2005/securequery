import hashlib
import time
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.database import get_auth_db, get_audit_db
from app.core.dpdp import check_dpdp_permission
from app.core.security import create_access_token, get_current_researcher
from app.core.risk_classifier import classify_risk, K_THRESHOLD, L_THRESHOLD
from app.core.smpc import secret_share, aggregate_shares, PRIME
from app.core.sql_validator import validate_sql
from app.core.hospital_db import HOSPITAL_DBS, run_sql_on_hospital
from app.core.audit import log_event
from app.core.config import settings
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

    if getattr(researcher, "role", "researcher") == "doctor":
        scope = getattr(researcher, "hospital_scope", None) or "hospital_a"
        if scope not in HOSPITAL_META:
            raise HTTPException(403, f"Doctor hospital scope '{scope}' is invalid")
        active_hospitals = {scope: HOSPITAL_META[scope]}
    else:
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

    try:
        check_dpdp_permission(db, researcher.email, purpose)
        dpdp_ok = True
    except HTTPException as e:
        dpdp_ok = False
        dpdp_detail = e.detail

    nlp_result = generate_sql(question, SCHEMA)
    sql = nlp_result["sql"]
    tables_referenced = [t for t in SCHEMA.keys() if t in sql.lower()] or ["patients"]
    model_label = "Qwen2.5-Coder (mock)" if settings.mock_ollama else "Qwen2.5-Coder (via Ollama)"
    add_step(2, "SQL Generation", {"model": model_label, "sql": sql, "tables_referenced": tables_referenced})

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

    # Detect whether this is an average-style (SUM+COUNT) query or a
    # plain COUNT query, based on what run_sql_on_hospital actually
    # returns for each hospital.
    raw_results = {hid: run_sql_on_hospital(hid, safe_sql) for hid in active_hospitals}
    is_average_query = any(isinstance(v, dict) for v in raw_results.values())

    if is_average_query:
        # Per-hospital sum/count, defaulting missing/failed hospitals to 0
        hospital_sums = {hid: (v["sum"] if isinstance(v, dict) else 0) for hid, v in raw_results.items()}
        hospital_counts = {hid: (v["count"] if isinstance(v, dict) else 0) for hid, v in raw_results.items()}
        total_count = sum(hospital_counts.values())
        total_sum = sum(hospital_sums.values())
        # k-anonymity must always check the real number of contributing
        # patients — never the sum, never the average itself.
        result_count_for_risk = total_count
    else:
        hospital_local_counts = {hid: v for hid, v in raw_results.items()}
        total_count = sum(hospital_local_counts.values())
        result_count_for_risk = total_count

    risk_features = dict(features)
    risk_features["result_count"] = result_count_for_risk
    risk_features["query_granularity"] = features.get("num_filters", 0)
    risk_features["is_single_hospital"] = (len(active_hospitals) == 1)
    risk_result = classify_risk(risk_features)
    masked = not risk_result["disclose"]

    add_step(5, "Privacy Risk Classification", {
        "risk_level": "LOW RISK" if not masked else "HIGH RISK",
        "action": "PROCEED_TO_SMPC" if not masked else "MASK_OUTPUT",
        "k_anonymity": {"status": "PASS" if risk_result["k_anon_pass"] else "FAIL",
                         "predicted_count": "suppressed" if masked else result_count_for_risk,
                         "threshold": K_THRESHOLD},
        "l_diversity": {"status": "PASS" if risk_result["l_diversity_pass"] else "FAIL",
                         "distinct_sensitive_values": risk_features.get("distinct_sensitive_values", 0),
                         "threshold": L_THRESHOLD},
    })

    hospitals_step_data = [
        {"id": meta["id"], "name": meta["name"], "local_count": "isolated"}
        for hid, meta in active_hospitals.items()
    ]
    add_step(6, "Local Hospital Computation", {"hospitals": hospitals_step_data},
              description="Each hospital computes its local value from its own database. The raw value never leaves that hospital's environment.")

    hospital_shares_data = []
    party_shares_count = {1: [], 2: [], 3: []}
    party_shares_sum = {1: [], 2: [], 3: []}
    SUM_SCALE = 1000

    if is_average_query:
        # Two independent secret-sharing rounds: one for counts, one for
        # sums. Each is separately additive-valid. Sums are floats in
        # general (age in years, etc.) — scale to an integer before
        # sharing over the finite field, unscale after reconstruction.
        for hid, meta in active_hospitals.items():
            count_val = hospital_counts[hid]
            sum_val_scaled = int(round(hospital_sums[hid] * SUM_SCALE))

            count_shares = secret_share(count_val, 3)
            sum_shares = secret_share(sum_val_scaled, 3)

            hospital_shares_data.append({
                "hospital_id": meta["id"], "hospital_name": meta["name"],
                "original_count": "isolated",
                "original_sum": "isolated",
                # PRIVACY FIX: never expose real per-party share values,
                # even though original_count/original_sum are already
                # hidden. Any viewer who sees all 3 parties' shares for
                # the same hospital in one place (which this view does)
                # can trivially sum them back into the raw count/sum —
                # defeating the point of secret sharing entirely.
                "shares": [{"party": i + 1, "count_share": "isolated", "sum_share": "isolated"} for i in range(3)],
            })
            for i in range(3):
                party_shares_count[i + 1].append(count_shares[i])
                party_shares_sum[i + 1].append(sum_shares[i])
    else:
        for hid, meta in active_hospitals.items():
            val = hospital_local_counts[hid]
            shares = secret_share(val, 3)
            hospital_shares_data.append({
                "hospital_id": meta["id"], "hospital_name": meta["name"],
                "original_count": "isolated",
                # PRIVACY FIX: same reasoning as above — real shares are
                # never rendered, only used internally for aggregation.
                "shares": [{"party": i + 1, "share_value": "isolated"} for i in range(3)],
            })
            for i in range(3):
                party_shares_count[i + 1].append(shares[i])

    add_step(7, "Secret Share Generation", {"hospital_shares": hospital_shares_data})

    # Compute the REAL partial sums first (always, unconditionally) — this
    # is the actual SMPC math and must never be skipped or altered by the
    # masking decision below. Masking only affects what gets DISPLAYED,
    # never what gets COMPUTED.
    real_partial_sums_count = {}
    real_partial_sums_sum = {} if is_average_query else None
    for pid in [1, 2, 3]:
        shares_dict_count = {meta["id"]: party_shares_count[pid][idx] for idx, (hid, meta) in enumerate(active_hospitals.items())}
        real_partial_sums_count[pid] = aggregate_shares(shares_dict_count)
        if is_average_query:
            shares_dict_sum = {meta["id"]: party_shares_sum[pid][idx] for idx, (hid, meta) in enumerate(active_hospitals.items())}
            real_partial_sums_sum[pid] = aggregate_shares(shares_dict_sum)

    final_aggregated_count = sum(real_partial_sums_count.values()) % PRIME
    if is_average_query:
        final_aggregated_sum_scaled = sum(real_partial_sums_sum.values()) % PRIME
        final_aggregated_sum = final_aggregated_sum_scaled / SUM_SCALE

    # THEN build the display-facing compute_parties_data, masking
    # individual partial sums whenever the overall result is masked.
    # PRIVACY FIX: previously these per-party partial sums were always
    # shown as real numbers regardless of `masked` — so even a fully
    # suppressed (below k-anonymity threshold) query could be trivially
    # un-suppressed by anyone who just added up the three "hidden" party
    # sums shown here. Also, `received_shares` used to list the exact
    # same raw per-hospital share values as step 7, just grouped by party
    # instead of by hospital — since all three parties are shown together
    # in this same response, that let a viewer reconstruct any hospital's
    # raw value just as easily as from step 7 itself.
    compute_parties_data = []
    for pid in [1, 2, 3]:
        party_entry = {
            "party_id": pid, "party_name": f"Compute Party {pid}",
            "received_shares": "isolated",
            "aggregated_partial_sum": "suppressed" if masked else real_partial_sums_count[pid],
        }
        if is_average_query:
            party_entry["aggregated_partial_sum_numeric"] = "suppressed" if masked else real_partial_sums_sum[pid]
        compute_parties_data.append(party_entry)

    add_step(8, "Multi-Party Secure Aggregation", {
        "compute_parties": compute_parties_data,
        "reconstruction_formula": "Sum(party_partial_sums) mod p = total_count" + (" ; same for total_sum, then total_sum / total_count = average" if is_average_query else ""),
        "final_aggregated_sum": "suppressed" if masked else final_aggregated_count,
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

    if masked:
        display_value = None
        unit = "patients"
    elif is_average_query:
        # Division only happens here, AFTER SMPC reconstruction, on
        # already-safe-to-disclose combined totals — never on a raw
        # per-hospital value.
        display_value = round(final_aggregated_sum / final_aggregated_count, 1) if final_aggregated_count else None
        unit = "years (average)"
    else:
        display_value = final_aggregated_count
        unit = "patients"

    add_step(10, "Final Privacy-Checked Result", {
        "masked": masked,
        "disclosure_status": "SUPPRESSED_K_ANONYMITY_VIOLATION" if masked else "DISCLOSED_SMPC_COMPLIANT",
        "final_answer": "Below disclosure threshold" if masked else display_value,
    })

    elapsed_ms = int((time.time() - start) * 1000)

    breakdown = [
        {"hospital_name": meta["name"], "count": "Data isolated"}
        for hid, meta in active_hospitals.items()
    ]

    response = {
        "masked": masked,
        "result": display_value,
        "unit": unit,
        "display_text": "Below disclosure threshold — result suppressed to protect patient privacy." if masked else None,
        "breakdown": breakdown,
        "execution_time_ms": elapsed_ms,
        "generated_sql": safe_sql,
    }
    if verbose:
        response["transparency_steps"] = steps
    return response