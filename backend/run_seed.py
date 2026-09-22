from sqlalchemy import text
from app.core.database import get_auth_db

db = next(get_auth_db())

# 1. Add hospital_scope column to researchers table if missing
db.execute(text("ALTER TABLE researchers ADD COLUMN IF NOT EXISTS hospital_scope VARCHAR(50) DEFAULT NULL;"))

# 2. Ensure EPIDEMIOLOGICAL_RESEARCH purpose exists in consent_purposes table
db.execute(text("""
INSERT INTO consent_purposes (purpose_id, purpose_code, description)
VALUES (gen_random_uuid(), 'EPIDEMIOLOGICAL_RESEARCH', 'Epidemiological Research')
ON CONFLICT (purpose_code) DO NOTHING;
"""))

# 3. Seed test Doctor account
seed_doctor_sql = """
INSERT INTO researchers (researcher_id, email, password_hash, full_name, role, hospital_scope, is_active, created_at)
VALUES (
    gen_random_uuid(),
    'dr_hospital_a@securequery.org',
    'dummy_hash',
    'Dr. Alice (Hospital A)',
    'doctor',
    'hospital_a',
    TRUE,
    NOW()
)
ON CONFLICT (email) DO UPDATE SET role = 'doctor', hospital_scope = 'hospital_a';
"""
db.execute(text(seed_doctor_sql))

# 4. Ensure ALL researchers have DPDP consent grants for EPIDEMIOLOGICAL_RESEARCH
grant_all_dpdp_sql = """
INSERT INTO researcher_permissions (permission_id, researcher_id, purpose_id, hospital_scope, data_localization_ok, granted_at)
SELECT gen_random_uuid(), r.researcher_id, p.purpose_id, 'all', TRUE, NOW()
FROM researchers r
CROSS JOIN consent_purposes p
WHERE p.purpose_code = 'EPIDEMIOLOGICAL_RESEARCH'
ON CONFLICT DO NOTHING;
"""
db.execute(text(grant_all_dpdp_sql))

db.commit()
print("All researchers granted DPDP consent for EPIDEMIOLOGICAL_RESEARCH!")
