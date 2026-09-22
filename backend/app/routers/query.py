from app.core.hospital_db import HOSPITAL_DBS, run_sql_on_hospital
import traceback
import psycopg2
import sqlglot
from sqlglot import exp
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_auth_db, get_audit_db
from app.core.dpdp import check_dpdp_permission
from app.core.risk_classifier import classify_risk, process_multivalue_result, build_analytics
from app.core.audit import log_event
from app.core.sql_validator import validate_sql
from app.nlp.pipeline import generate_sql
from app.nlp.feature_extractor import extract_features
from app.schemas.mock_schema import SCHEMA
from app.routers.auth import get_current_user
from app.models.auth_models import Researcher

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    question: str
    purpose: str


def adapt_sql_for_single_hospital(sql: str) -> str:
    """
    Each hospital's DB only contains that hospital's own data, so any
    hospital_id column/GROUP BY/HAVING referring to cross-hospital grouping
    needs to be stripped — via the AST, not fragile string replace.
    """
    tree = sqlglot.parse_one(sql, read="postgres")

    tree.set("group", None)
    tree.set("having", None)

    new_expressions = [
        e for e in tree.expressions
        if not (isinstance(e, exp.Column) and e.name.lower() == "hospital_id")
    ]
    tree.set("expressions", new_expressions)

    return tree.sql(dialect="postgres")


@router.post("/ask")
def ask_query(
    payload: QueryRequest,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_auth_db),
    audit_db: Session = Depends(get_audit_db),
):
    try:
        check_dpdp_permission(db, current_user, payload.purpose)
        researcher = db.query(Researcher).filter(Researcher.email == current_user).first()

        nlp_result = generate_sql(payload.question, SCHEMA)
        generated_sql = nlp_result["sql"]

        validation = validate_sql(generated_sql, SCHEMA)
        if not validation["valid"]:
            raise HTTPException(status_code=400, detail=f"Invalid SQL: {validation['errors']}")

        safe_sql = validation["sql"]
        features = extract_features(safe_sql, SCHEMA)

        per_hospital_results = []
        for hospital_id in HOSPITAL_DBS.keys():
            try:
                raw_value = run_sql_on_hospital(hospital_id, safe_sql)
            except Exception:
                raw_value = 0

            hospital_features = dict(features)
            hospital_features["result_count"] = raw_value
            hospital_features["query_granularity"] = features.get("num_filters", 0)
            hospital_features["is_single_hospital"] = True
            # distinct_sensitive_values kept as computed by extract_features — not overridden

            per_hospital_results.append({
                "group_key": hospital_id,
                "raw_value": raw_value,
                "features": hospital_features,
            })

        processed = process_multivalue_result(per_hospital_results)
        analytics = build_analytics(processed)
        overall_disclosed = any(r["disclosed"] for r in processed)
        total_value = sum(
            r["value"] for r in processed
            if r.get("disclosed") and isinstance(r.get("value"), (int, float))
        )

        log_event(
            audit_db,
            researcher_id=researcher.researcher_id,
            query_text=payload.question,
            generated_sql=safe_sql,
            dpdp_check_result="passed",
            risk_check_result="processed",
            disclosed=overall_disclosed,
        )

        # --- Privacy fix: never expose per-hospital raw values, anywhere ---
        # SMPC's guarantee is that no party's individual input ever reaches
        # the researcher's screen, regardless of whether the aggregate is
        # safe to disclose. Only the combined total is safe to show.
        masked_results = [
            {
                "group_key": r["group_key"],
                "disclosed": "isolated",
                "value": "isolated",
                "risk_result": r.get("risk_result"),
            }
            for r in processed
        ]

        masked_analytics = {
            "stats": analytics.get("stats", {}),
            "charts": [
                {**chart, "values": [0 for _ in chart.get("values", [])]}
                for chart in analytics.get("charts", [])
            ],
            "tables": [
                {
                    **table,
                    "rows": [
                        {**row, "value": "isolated"} for row in table.get("rows", [])
                    ],
                }
                for table in analytics.get("tables", [])
            ],
        }

        return {
            "question": payload.question,
            "purpose": payload.purpose,
            "generated_sql": safe_sql,
            "total_disclosed_value": total_value if overall_disclosed else None,
            "results": masked_results,
            "analytics": masked_analytics,
        }

    except HTTPException:
        raise
    except Exception as e:
        err_msg = f"QUERY_PIPELINE_ERROR: {str(e)}\n{traceback.format_exc()}"
        print(err_msg)
        raise HTTPException(status_code=500, detail=err_msg)