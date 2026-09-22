from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException, status
from app.models.auth_models import Researcher, ConsentPurpose, ResearcherPermission

def check_dpdp_permission(db: Session, email: str, requested_purpose: str) -> bool:
    """
    Verifies the researcher has explicit consent-purpose approval
    under DPDP guidelines. Checks ORM permission tables first, with fallback to dpdp_grants.
    Raises 403 if not authorized.
    """
    researcher = db.query(Researcher).filter(Researcher.email == email).first()
    if not researcher:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Researcher not found")

    # 1. Check ORM tables (ResearcherPermission + ConsentPurpose)
    try:
        permission = (
            db.query(ResearcherPermission)
            .join(ConsentPurpose, ResearcherPermission.purpose_id == ConsentPurpose.purpose_id)
            .filter(
                ResearcherPermission.researcher_id == researcher.researcher_id,
                ConsentPurpose.purpose_code == requested_purpose,
            )
            .first()
        )

        if permission:
            if permission.expires_at is not None:
                expires_at = permission.expires_at
                now = datetime.now(timezone.utc).replace(tzinfo=None) if expires_at.tzinfo is None else datetime.now(timezone.utc)
                if expires_at < now:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"DPDP compliance check failed: permission for '{requested_purpose}' has expired",
                    )

            if hasattr(permission, "data_localization_ok") and not permission.data_localization_ok:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Data localization check failed for purpose '{requested_purpose}'",
                )

            return True
    except Exception:
        # Fall through to raw table check on ORM query errors
        pass

    # 2. Fallback: Check dpdp_grants table directly
    try:
        check_sql = text("""
            SELECT 1 FROM dpdp_grants 
            WHERE researcher_id = :rid AND purpose = :purpose
        """)
        res = db.execute(check_sql, {"rid": researcher.researcher_id, "purpose": requested_purpose}).first()
        if res:
            return True
    except Exception:
        pass

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"DPDP compliance check failed: researcher '{email}' is not authorized for purpose '{requested_purpose}'",
    )