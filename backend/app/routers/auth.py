import traceback
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import create_access_token, decode_access_token, verify_password
from app.core.audit import log_event, get_audit_log, verify_chain_integrity
from app.core.risk_classifier import classify_risk
from app.core.database import get_auth_db, get_audit_db
from app.core.dpdp import check_dpdp_permission
from app.models.auth_models import Researcher

router = APIRouter(prefix="/auth", tags=["auth"])
security_bearer = HTTPBearer()

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_bearer)) -> str:
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload["sub"]

@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_auth_db),
    audit_db: Session = Depends(get_audit_db)
):
    try:
        researcher = db.query(Researcher).filter(Researcher.email == payload.email).first()
        if not researcher or not researcher.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        if not verify_password(payload.password, researcher.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        
        try:
            log_event(
                audit_db,
                researcher_id=researcher.researcher_id,
                query_text="LOGIN",
                dpdp_check_result="n/a",
                risk_check_result="n/a",
                disclosed=None,
            )
        except Exception as audit_err:
            print(f"WARNING: Audit log failed during login: {audit_err}")

        token = create_access_token(data={"sub": researcher.email})
        return LoginResponse(access_token=token)
    except HTTPException:
        raise
    except Exception as e:
        err_detail = f"LOGIN_FAILED: {str(e)}\n{traceback.format_exc()}"
        print(err_detail)
        raise HTTPException(status_code=500, detail=err_detail)

@router.get("/me")
def read_current_user(current_user: str = Depends(get_current_user)):
    return {"username": current_user}

@router.get("/test-dpdp")
def test_dpdp(
    purpose: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_auth_db),
    audit_db: Session = Depends(get_audit_db),
):
    researcher = db.query(Researcher).filter(Researcher.email == current_user).first()
    check_dpdp_permission(db, current_user, purpose)
    
    log_event(
        audit_db,
        researcher_id=researcher.researcher_id,
        query_text=f"DPDP_CHECK:{purpose}",
        dpdp_check_result="passed",
    )
    
    return {"status": "authorized", "user": current_user, "purpose": purpose}

@router.get("/test-risk")
def test_risk(
    result_count: int,
    distinct_sensitive_values: int,
    query_granularity: int,
    is_single_hospital: bool,
    purpose: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_auth_db),
    audit_db: Session = Depends(get_audit_db),
):
    researcher = db.query(Researcher).filter(Researcher.email == current_user).first()
    check_dpdp_permission(db, current_user, purpose)
    
    risk_result = classify_risk({
        "result_count": result_count,
        "distinct_sensitive_values": distinct_sensitive_values,
        "query_granularity": query_granularity,
        "is_single_hospital": is_single_hospital,
    })
    
    log_event(
        audit_db,
        researcher_id=researcher.researcher_id,
        query_text=f"RISK_CHECK:{purpose}",
        dpdp_check_result="passed",
        risk_check_result="risky" if risk_result["risk_score"] > 0.5 else "low_risk",
        disclosed=risk_result["disclose"],
    )
    
    return {"user": current_user, "purpose": purpose, "risk_result": risk_result}

@router.get("/audit-log")
def view_audit_log(audit_db: Session = Depends(get_audit_db)):
    return {
        "chain_valid": verify_chain_integrity(audit_db),
        "entries": get_audit_log(audit_db),
    }