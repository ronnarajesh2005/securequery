import hashlib
import json
from sqlalchemy.orm import Session
from app.models.auth_models import AuditLog


def _compute_hash(entry_dict: dict, prev_hash: str) -> str:
    payload = json.dumps(entry_dict, sort_keys=True, default=str) + (prev_hash or "GENESIS")
    return hashlib.sha256(payload.encode()).hexdigest()


def log_event(
    db: Session,
    researcher_id: str,
    query_text: str,
    generated_sql: str = None,
    dpdp_check_result: str = None,
    risk_check_result: str = None,
    disclosed: bool = None,
) -> AuditLog:
    """
    Appends a new audit entry, hash-chained to the previous entry in audit_log.
    """
    last_entry = db.query(AuditLog).order_by(AuditLog.entry_id.desc()).first()
    prev_hash = last_entry.entry_hash if last_entry else None

    entry_fields = {
        "researcher_id": str(researcher_id),
        "query_text": query_text,
        "generated_sql": generated_sql,
        "dpdp_check_result": dpdp_check_result,
        "risk_check_result": risk_check_result,
        "disclosed": disclosed,
    }
    entry_hash = _compute_hash(entry_fields, prev_hash)

    new_entry = AuditLog(
        researcher_id=researcher_id,
        query_text=query_text,
        generated_sql=generated_sql,
        dpdp_check_result=dpdp_check_result,
        risk_check_result=risk_check_result,
        disclosed=disclosed,
        entry_data=json.dumps(entry_fields, default=str),
        entry_hash=entry_hash,
        prev_hash=prev_hash,
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return new_entry


def get_audit_log(db: Session) -> list[dict]:
    entries = db.query(AuditLog).order_by(AuditLog.entry_id.asc()).all()
    return [
        {
            "entry_id": e.entry_id,
            "researcher_id": str(e.researcher_id),
            "query_text": e.query_text,
            "generated_sql": e.generated_sql,
            "dpdp_check_result": e.dpdp_check_result,
            "risk_check_result": e.risk_check_result,
            "disclosed": e.disclosed,
            "prev_hash": e.prev_hash,
            "entry_hash": e.entry_hash,
            "created_at": str(e.created_at),
        }
        for e in entries
    ]


def verify_chain_integrity(db: Session) -> bool:
    entries = db.query(AuditLog).order_by(AuditLog.entry_id.asc()).all()
    for i, e in enumerate(entries):
        expected_prev = entries[i - 1].entry_hash if i > 0 else None
        if e.prev_hash != expected_prev:
            return False

        entry_fields = {
            "researcher_id": str(e.researcher_id),
            "query_text": e.query_text,
            "generated_sql": e.generated_sql,
            "dpdp_check_result": e.dpdp_check_result,
            "risk_check_result": e.risk_check_result,
            "disclosed": e.disclosed,
        }
        recomputed = _compute_hash(entry_fields, e.prev_hash)
        if recomputed != e.entry_hash:
            return False

    return True