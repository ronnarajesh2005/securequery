from app.core.database import auth_engine
from sqlalchemy import text

migration_sql = '''
ALTER TABLE researchers ADD COLUMN IF NOT EXISTS hospital_scope VARCHAR(50) DEFAULT NULL;

INSERT INTO researchers (researcher_id, email, password_hash, full_name, role, hospital_scope, is_active, created_at)
VALUES (
    gen_random_uuid(),
    'dr_hospital_a@securequery.org',
    '\\\',
    'Dr. Alice (Hospital A)',
    'doctor',
    'hospital_a',
    TRUE,
    NOW()
) ON CONFLICT (email) DO UPDATE SET role = 'doctor', hospital_scope = 'hospital_a';
'''

with auth_engine.connect() as connection:
    connection.execute(text(migration_sql))
    connection.commit()
    print("Migration executed successfully!")
