from app.core.database import get_auth_db
from app.models.auth_models import Researcher
from sqlalchemy import text

db = next(get_auth_db())
try:
    doc = db.query(Researcher).filter(Researcher.email == 'dr_hospital_a@securequery.org').first()
    if doc:
        sql = '''
        INSERT INTO dpdp_grants (grant_id, researcher_id, purpose, granted_at)
        VALUES (gen_random_uuid(), :rid, 'EPIDEMIOLOGICAL_RESEARCH', NOW())
        ON CONFLICT DO NOTHING;
        '''
        db.execute(text(sql), {"rid": doc.researcher_id})
        db.commit()
        print('Successfully added DPDP consent grant for dr_hospital_a!')
    else:
        print('Doctor account not found.')
except Exception as e:
    db.rollback()
    print(f'Error: {e}')
finally:
    db.close()
