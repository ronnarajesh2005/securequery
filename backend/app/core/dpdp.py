from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.auth_models import Researcher, ConsentPurpose, ResearcherPermission

def check_dpdp_permission(db: Session, email: str, requested_purpose: str) -> bool:
    """
    Verifies the researcher has explicit, non-expired consent-purpose approval
    AND passes the data localization check, for the specific research purpose
    they're querying under. Raises 403 if not authorized.
    """
    researcher = db.query(Researcher).filter(Researcher.email == email).first()
    if not researcher:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Researcher not found")

    permission = (
        db.query(ResearcherPermission)
        .join(ConsentPurpose, ResearcherPermission.purpose_id == ConsentPurpose.purpose_id)
        .filter(
            ResearcherPermission.researcher_id == researcher.researcher_id,
            ConsentPurpose.purpose_code == requested_purpose,
        )
        .first()
    )

    if not permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"DPDP compliance check failed: researcher '{email}' is not authorized for purpose '{requested_purpose}'",
        )

    if permission.expires_at is not None:
        # Handle naive or aware datetime objects safely
        expires_at = permission.expires_at
        if expires_at.tzinfo is None:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
        else:
            now = datetime.now(timezone.utc)

        if expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"DPDP compliance check failed: permission for '{requested_purpose}' has expired",
            )

    if not permission.data_localization_ok:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Data localization check failed for purpose '{requested_purpose}'",
        )

    return True