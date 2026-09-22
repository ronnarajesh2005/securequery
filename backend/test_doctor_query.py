import traceback
from app.core.database import get_auth_db, get_audit_db
from app.models.auth_models import Researcher
from app.routers.dashboard import dashboard_query

db = next(get_auth_db())
audit_db = next(get_audit_db())

try:
    doc = db.query(Researcher).filter(Researcher.email == 'dr_hospital_a@securequery.org').first()
    print(f'Found Researcher: {doc.email}, Role: {doc.role}, Scope: {doc.hospital_scope}')
    
    payload = {"question": "How many patients have diabetes?"}
    res = dashboard_query(payload=payload, verbose=False, researcher=doc, db=db, audit_db=audit_db)
    print("SUCCESS RESULT:")
    print(res)
except Exception as e:
    print("--- TRACEBACK ERROR DETAIL ---")
    traceback.print_exc()
finally:
    db.close()
    audit_db.close()
