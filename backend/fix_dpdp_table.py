from app.core.database import get_auth_db
from app.models.auth_models import Researcher
from sqlalchemy import text

db = next(get_auth_db())
try:
    # 1. Create table if missing
    create_table_sql = '''
    CREATE TABLE IF NOT EXISTS dpdp_grants (
        grant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        researcher_id UUID NOT NULL REFERENCES researchers(researcher_id) ON DELETE CASCADE,
        purpose VARCHAR(100) NOT NULL,
        granted_at TIMESTAMP DEFAULT NOW()
    );
    '''
    db.execute(text(create_table_sql))
    
    # 2. Add grants for all researchers
    researchers = db.query(Researcher).all()
    for r in researchers:
        insert_grant_sql = '''
        INSERT INTO dpdp_grants (grant_id, researcher_id, purpose, granted_at)
        VALUES (gen_random_uuid(), :rid, 'EPIDEMIOLOGICAL_RESEARCH', NOW());
        '''
        db.execute(text(insert_grant_sql), {"rid": r.researcher_id})

    db.commit()
    print("Created dpdp_grants table and granted EPIDEMIOLOGICAL_RESEARCH permission to all users!")
except Exception as e:
    db.rollback()
    print(f"Error: {e}")
finally:
    db.close()
