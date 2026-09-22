import psycopg2
import random

INDIAN_FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan",
    "Krishna", "Ishaan", "Rohan", "Kabir", "Aryan", "Dhruv", "Karthik",
    "Saanvi", "Ananya", "Diya", "Aadhya", "Kavya", "Anika", "Ira", "Myra",
    "Sara", "Pari", "Riya", "Isha", "Neha", "Priya", "Sneha", "Divya",
    "Rajesh", "Suresh", "Ramesh", "Mahesh", "Ganesh", "Vijay", "Anil",
    "Sunita", "Kavita", "Lakshmi", "Meera", "Pooja", "Anita", "Geeta"
]

INDIAN_LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Kumar", "Singh", "Patel", "Reddy", "Rao",
    "Nair", "Iyer", "Menon", "Pillai", "Chatterjee", "Banerjee", "Mukherjee",
    "Das", "Ghosh", "Bose", "Joshi", "Desai", "Shah", "Mehta", "Kapoor",
    "Malhotra", "Chopra", "Agarwal", "Bansal", "Jain", "Yadav", "Choudhary"
]

INDIAN_LOCATIONS = [
    ("Bengaluru", "Karnataka", "560001"),
    ("Mumbai", "Maharashtra", "400001"),
    ("Chennai", "Tamil Nadu", "600001"),
    ("Hyderabad", "Telangana", "500001"),
    ("Pune", "Maharashtra", "411001"),
    ("Delhi", "Delhi", "110001"),
    ("Kolkata", "West Bengal", "700001"),
    ("Ahmedabad", "Gujarat", "380001"),
    ("Jaipur", "Rajasthan", "302001"),
    ("Lucknow", "Uttar Pradesh", "226001"),
    ("Kochi", "Kerala", "682001"),
    ("Chandigarh", "Chandigarh", "160001"),
]

HOSPITALS = {
    "Hospital A": {
        "host": "localhost",
        "port": 5433,
        "database": "hospital_a",
        "user": "hospital_a_admin",
        "password": "HospitalA_2026!",
    },
    "Hospital C": {
        "host": "localhost",
        "port": 5435,
        "database": "hospital_c",
        "user": "hospital_c_admin",
        "password": "HospitalC_2026!",
    },
}

def indianize(db_config, label):
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    cur.execute("SELECT patient_id FROM patients")
    patient_ids = [row[0] for row in cur.fetchall()]
    print(f"Found {len(patient_ids)} patients to Indianize in {label}...")
    updated = 0
    for pid in patient_ids:
        first = random.choice(INDIAN_FIRST_NAMES)
        last = random.choice(INDIAN_LAST_NAMES)
        city, state, zip_code = random.choice(INDIAN_LOCATIONS)
        cur.execute(
            """
            UPDATE patients
            SET first_name = %s, last_name = %s, city = %s, state = %s, zip_code = %s
            WHERE patient_id = %s
            """,
            (first, last, city, state, zip_code, pid),
        )
        updated += 1
        if updated % 200 == 0:
            print(f"  ...{updated} updated")
    conn.commit()
    print(f"Done. {updated} patients Indianized in {label}.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    for label, config in HOSPITALS.items():
        print(f"\n=== {label} ===")
        indianize(config, label)