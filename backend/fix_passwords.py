from app.core.database import get_auth_db
from app.core.security import hash_password
from sqlalchemy import text

valid_hash = hash_password("password123")

update_sql = '''
INSERT INTO researchers (researcher_id, email, password_hash, full_name, role, hospital_scope, is_active, created_at)
VALUES (
    gen_random_uuid(),
    'dr_test@securequery.org',
    :pwd_hash,
    'Dr. Test Researcher',
    'researcher',
    NULL,
    TRUE,
    NOW()
) ON CONFLICT (email) DO UPDATE 
SET password_hash = :pwd_hash, role = 'researcher';

INSERT INTO researchers (researcher_id, email, password_hash, full_name, role, hospital_scope, is_active, created_at)
VALUES (
    gen_random_uuid(),
    'dr_hospital_a@securequery.org',
    :pwd_hash,
    'Dr. Alice (Hospital A)',
    'doctor',
    'hospital_a',
    TRUE,
    NOW()
) ON CONFLICT (email) DO UPDATE 
SET password_hash = :pwd_hash, role = 'doctor', hospital_scope = 'hospital_a';
'''

db = next(get_auth_db())
try:
    db.execute(text(update_sql), {"pwd_hash": valid_hash})
    db.commit()
    print("Successfully updated database records for dr_test and dr_hospital_a with valid bcrypt hashes!")
except Exception as e:
    db.rollback()
    print(f"Database update failed: {e}")
finally:
    db.close()
