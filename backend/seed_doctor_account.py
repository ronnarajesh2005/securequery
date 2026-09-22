import sys
sys.path.insert(0, r"D:\securequery\backend")

import psycopg2
from app.core.security import hash_password

AUTH_DB_CONFIG = {
    "host": "localhost",
    "port": 5436,
    "database": "auth_db",
    "user": "auth_admin",
    "password": "AuthDB_2026!",
}

def seed_doctor():
    conn = psycopg2.connect(**AUTH_DB_CONFIG)
    cur = conn.cursor()

    hashed_pw = hash_password("doctorpass123")

    cur.execute(
        """
        INSERT INTO researchers (email, password_hash, full_name, role, hospital_scope, is_active)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (email) DO UPDATE SET
            password_hash = EXCLUDED.password_hash,
            role = EXCLUDED.role,
            hospital_scope = EXCLUDED.hospital_scope,
            is_active = TRUE
        RETURNING researcher_id
        """,
        ("dr_hospital_a@securequery.org", hashed_pw, "Dr. Hospital A Doctor", "doctor", "hospital_a", True),
    )
    researcher_id = cur.fetchone()[0]
    print(f"Doctor confirmed: dr_hospital_a@securequery.org -> {researcher_id}")

    conn.commit()
    cur.close()
    conn.close()
    print("\nDoctor account seeded and ready.")

if __name__ == "__main__":
    seed_doctor()