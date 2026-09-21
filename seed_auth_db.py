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

def seed():
    conn = psycopg2.connect(**AUTH_DB_CONFIG)
    cur = conn.cursor()

    # 1. Insert consent purposes safely
    purposes = [
        ("diabetes_surveillance", "Diabetes prevalence and trend surveillance"),
        ("hypertension_surveillance", "Hypertension prevalence and trend surveillance"),
    ]
    purpose_ids = {}
    for code, desc in purposes:
        cur.execute(
            """
            INSERT INTO consent_purposes (purpose_code, description)
            VALUES (%s, %s)
            ON CONFLICT (purpose_code) DO UPDATE SET description = EXCLUDED.description
            RETURNING purpose_id
            """,
            (code, desc),
        )
        purpose_ids[code] = cur.fetchone()[0]
        print(f"Purpose confirmed: {code} -> {purpose_ids[code]}")

    # 2. Insert test researcher safely
    hashed_pw = hash_password("testpass123")
    cur.execute(
        """
        INSERT INTO researchers (email, password_hash, full_name, role, is_active)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (email) DO UPDATE SET is_active = TRUE
        RETURNING researcher_id
        """,
        ("dr_test@securequery.org", hashed_pw, "Dr. Test Researcher", "researcher", True),
    )
    researcher_id = cur.fetchone()[0]
    print(f"Researcher confirmed: dr_test@securequery.org -> {researcher_id}")

    # 3. Grant permissions safely
    for code, pid in purpose_ids.items():
        cur.execute(
            """
            INSERT INTO researcher_permissions
                (researcher_id, purpose_id, hospital_scope, data_localization_ok)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (researcher_id, pid, "all", True),
        )
        print(f"Permission confirmed for: {code}")

    conn.commit()
    cur.close()
    conn.close()
    print("\nAuth DB state verified and ready.")

if __name__ == "__main__":
    seed()