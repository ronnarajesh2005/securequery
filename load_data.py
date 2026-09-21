"""
load_data.py

Reads a hospital's Indianized Synthea CSV export (patients.csv + conditions.csv)
and loads it into that hospital's own Postgres database. Never touches another
hospital's database -- the --hospital flag picks exactly one target.

Loads:
  - patients:   patient_id, first_name, last_name, date_of_birth, gender,
                zip_code, city, state
  - conditions: condition_id, patient_id, condition_code, condition_desc,
                onset_date, resolved_date
    (encounter_id is left NULL -- we are not loading the encounters table,
    and the schema allows encounter_id to be nullable)

Conditions are filtered to NCD-relevant entries (diabetes, hypertension,
cardiovascular disease and related terms) to match the project's stated
scope and keep load times reasonable, since Synthea's raw conditions.csv
contains many unrelated diagnoses (fractures, infections, checkups, etc.)

Usage:
    python load_data.py --hospital a --data-dir ./indianized/hospital_a
    python load_data.py --hospital b --data-dir ./indianized/hospital_b
    python load_data.py --hospital c --data-dir ./indianized/hospital_c
"""

import argparse
import os
import sys
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

# Maps --hospital flag to (port, dbname, env var prefix)
HOSPITAL_CONFIG = {
    "a": {"port": 5433, "dbname": "hospital_a", "env_prefix": "HOSPITAL_A"},
    "b": {"port": 5434, "dbname": "hospital_b", "env_prefix": "HOSPITAL_B"},
    "c": {"port": 5435, "dbname": "hospital_c", "env_prefix": "HOSPITAL_C"},
}

# Keywords used to filter conditions.csv down to NCD-relevant rows.
# Case-insensitive substring match against the DESCRIPTION column.
NCD_KEYWORDS = [
    "diabetes", "hypertension", "blood pressure", "cardiovascular",
    "heart disease", "myocardial", "coronary", "stroke", "cerebrovascular",
    "hyperlipidemia", "cholesterol",
]


def load_env(env_path: str) -> dict:
    """Minimal .env parser -- avoids adding python-dotenv as a dependency."""
    env = {}
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip()
    return env


def get_connection(hospital: str, env: dict):
    config = HOSPITAL_CONFIG[hospital]
    user = env[f"{config['env_prefix']}_USER"]
    password = env[f"{config['env_prefix']}_PASSWORD"]
    return psycopg2.connect(
        host="localhost",
        port=config["port"],
        dbname=config["dbname"],
        user=user,
        password=password,
    )


def load_patients(conn, patients_csv: str) -> int:
    df = pd.read_csv(patients_csv)

    rows = []
    for _, r in df.iterrows():
        rows.append((
            r["Id"],
            r["FIRST"],
            r["LAST"],
            r["BIRTHDATE"],
            r["GENDER"],
            str(r["ZIP"]) if pd.notna(r.get("ZIP")) else None,
            r.get("CITY"),
            r.get("STATE"),
        ))

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO patients (patient_id, first_name, last_name, date_of_birth, gender, zip_code, city, state)
            VALUES %s
            ON CONFLICT (patient_id) DO NOTHING
            """,
            rows,
        )
    conn.commit()
    return len(rows)


def load_conditions(conn, conditions_csv: str) -> tuple[int, int]:
    df = pd.read_csv(conditions_csv)

    pattern = "|".join(NCD_KEYWORDS)
    filtered = df[df["DESCRIPTION"].str.contains(pattern, case=False, na=False)]

    rows = []
    for _, r in filtered.iterrows():
        rows.append((
            r["PATIENT"],
            r["CODE"],
            r["DESCRIPTION"],
            r["START"],
            r["STOP"] if pd.notna(r.get("STOP")) else None,
        ))

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO conditions (patient_id, condition_code, condition_desc, onset_date, resolved_date)
            VALUES %s
            """,
            rows,
        )
    conn.commit()
    return len(df), len(rows)


def main():
    parser = argparse.ArgumentParser(description="Load Indianized Synthea data into a hospital's Postgres database.")
    parser.add_argument("--hospital", required=True, choices=["a", "b", "c"], help="Which hospital to load (a, b, or c)")
    parser.add_argument("--data-dir", required=True, help="Path to that hospital's indianized folder (contains patients.csv, conditions.csv)")
    parser.add_argument("--env-file", default="../docker/.env", help="Path to the .env file with DB credentials")
    args = parser.parse_args()

    env = load_env(args.env_file)
    conn = get_connection(args.hospital, env)

    patients_csv = os.path.join(args.data_dir, "patients.csv")
    conditions_csv = os.path.join(args.data_dir, "conditions.csv")

    print(f"Loading Hospital {args.hospital.upper()} into database '{HOSPITAL_CONFIG[args.hospital]['dbname']}' ...")

    n_patients = load_patients(conn, patients_csv)
    print(f"  Inserted {n_patients} patients.")

    total_conditions, n_conditions = load_conditions(conn, conditions_csv)
    print(f"  Inserted {n_conditions} NCD-relevant conditions (out of {total_conditions} total condition entries).")

    conn.close()
    print(f"Done loading Hospital {args.hospital.upper()}.")


if __name__ == "__main__":
    main()
