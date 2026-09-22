import psycopg2

# ============================================================
# NFHS-5 BASELINE
# ============================================================

NFHS_DIABETES = 3.79
NFHS_HYPERTENSION = 21.81

# Actual SNOMED codes found in Hospital A
DIABETES_CODES = ("44054006",)
HYPERTENSION_CODES = ("59621000",)


# ============================================================
# HOSPITAL DATABASE CONFIGURATION
# ============================================================

HOSPITALS = {
    "Hospital A": {
        "host": "localhost",
        "port": 5433,
        "database": "hospital_a",
        "user": "hospital_a_admin",
        "password": "HospitalB_2026!"
    },

    "Hospital B": {
        "host": "localhost",
        "port": 5434,
        "database": "hospital_b",
        "user": "hospital_b_admin",
        "password": "HospitalB_2026!"
    },

    "Hospital C": {
        "host": "localhost",
        "port": 5435,
        "database": "hospital_c",
        "user": "hospital_c_admin",
        "password": "HospitalB_2026!"
    }
}


# ============================================================
# GET PREVALENCE FROM ONE HOSPITAL
# ============================================================

def get_prevalence(config):

    conn = psycopg2.connect(**config)
    cur = conn.cursor()

    # Total number of patients
    cur.execute("""
        SELECT COUNT(*)
        FROM patients;
    """)

    total_patients = cur.fetchone()[0]

    # Diabetes patients
    cur.execute("""
        SELECT COUNT(DISTINCT patient_id)
        FROM conditions
        WHERE condition_code IN %s;
    """, (DIABETES_CODES,))

    diabetes_patients = cur.fetchone()[0]

    # Hypertension patients
    cur.execute("""
        SELECT COUNT(DISTINCT patient_id)
        FROM conditions
        WHERE condition_code IN %s;
    """, (HYPERTENSION_CODES,))

    hypertension_patients = cur.fetchone()[0]

    cur.close()
    conn.close()

    diabetes_rate = (diabetes_patients / total_patients) * 100
    hypertension_rate = (hypertension_patients / total_patients) * 100

    return (
        total_patients,
        diabetes_patients,
        diabetes_rate,
        hypertension_patients,
        hypertension_rate
    )


# ============================================================
# MAIN
# ============================================================

print("=" * 70)
print("       SYNTHETIC HOSPITAL DATA vs NFHS-5 BASELINE")
print("=" * 70)

print(f"\nNFHS-5 Diabetes:      {NFHS_DIABETES:.2f}%")
print(f"NFHS-5 Hypertension:  {NFHS_HYPERTENSION:.2f}%")

print("\n" + "-" * 70)

for hospital_name, config in HOSPITALS.items():

    try:

        (
            total,
            diabetes_patients,
            diabetes_rate,
            hypertension_patients,
            hypertension_rate
        ) = get_prevalence(config)

        diabetes_difference = diabetes_rate - NFHS_DIABETES
        hypertension_difference = (
            hypertension_rate - NFHS_HYPERTENSION
        )

        print(f"\n{hospital_name}")
        print(f"Total patients:          {total}")

        print(
            f"Diabetes:                "
            f"{diabetes_rate:.2f}% "
            f"({diabetes_patients} patients)"
        )

        print(
            f"Difference from NFHS:   "
            f"{diabetes_difference:+.2f} percentage points"
        )

        print(
            f"Hypertension:            "
            f"{hypertension_rate:.2f}% "
            f"({hypertension_patients} patients)"
        )

        print(
            f"Difference from NFHS:   "
            f"{hypertension_difference:+.2f} percentage points"
        )

        print("-" * 70)

    except Exception as e:

        print(f"\n{hospital_name}: ERROR")
        print(e)
        print("-" * 70)