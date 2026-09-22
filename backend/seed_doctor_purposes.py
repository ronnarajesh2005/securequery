import sys
sys.path.insert(0, r"D:\securequery\backend")
import psycopg2

AUTH_DB_CONFIG = {
    "host": "localhost", "port": 5436, "database": "auth_db",
    "user": "auth_admin", "password": "AuthDB_2026!",
}

def seed():
    conn = psycopg2.connect(**AUTH_DB_CONFIG)
    cur = conn.cursor()

    # Get doctor researcher ID
    cur.execute("SELECT researcher_id FROM researchers WHERE email = %s", ("dr_hospital_a@securequery.org",))
    row = cur.fetchone()
    if not row:
        print("Error: dr_hospital_a@securequery.org not found in database. Run the doctor-seeding script first.")
        conn.close()
        return
    researcher_id = row[0]

    # NOTE: COMMERCIAL_MARKETING is intentionally NOT seeded (triggers genuine 403 DPDP rejection)
    purposes = [
        ("EPIDEMIOLOGICAL_RESEARCH", "General epidemiological research across hospital network"),
        ("PUBLIC_HEALTH_SURVEILLANCE", "Public health surveillance and NCD tracking"),
    ]

    for code, desc in purposes:
        # Check if purpose already exists
        cur.execute("SELECT purpose_id FROM consent_purposes WHERE purpose_code = %s", (code,))
        p_row = cur.fetchone()
        if p_row:
            purpose_id = p_row[0]
        else:
            cur.execute(
                "INSERT INTO consent_purposes (purpose_code, description) VALUES (%s, %s) RETURNING purpose_id",
                (code, desc),
            )
            purpose_id = cur.fetchone()[0]

        # Check if permission already exists
        cur.execute(
            "SELECT permission_id FROM researcher_permissions WHERE researcher_id = %s AND purpose_id = %s",
            (researcher_id, purpose_id)
        )
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO researcher_permissions (researcher_id, purpose_id, hospital_scope, data_localization_ok) VALUES (%s, %s, %s, %s)",
                (researcher_id, purpose_id, "hospital_a", True),
            )
            print(f"Granted permission: {code} (scope: hospital_a)")
        else:
            print(f"Already granted: {code}")

    conn.commit()
    cur.close()
    conn.close()
    print("Doctor consent seeding complete.")

if __name__ == "__main__":
    seed()