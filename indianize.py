"""
indianize.py

Converts a Synthea CSV export's patients.csv identity and address fields
(first name, last name, address, city, state, zip) to Indian equivalents
using Faker's en_IN locale. Clinical files (conditions.csv, medications.csv,
observations.csv, encounters.csv, etc.) are copied over UNCHANGED, since
their SNOMED/RxNorm/LOINC codes are international standards, not tied to
any country.

DESIGN DECISION (documented here per the task instructions, not left silent):
RACE and ETHNICITY columns are DROPPED, not relabeled. Synthea's values for
these (e.g. "white", "black", "nonhispanic") are US Census categories with
no clean one-to-one Indian equivalent, and keeping them as-is in an
"Indian hospital" demo dataset would look factually wrong. If your team
later decides these columns are needed for a specific analysis, they can
be re-added with a proper Indian demographic scheme (e.g. religion/region
based categories used in Indian census data) rather than mapped from the
US categories.

Usage:
    python indianize.py --input ./output/hospital_a/csv --output ./indianized/hospital_a --seed 1001
"""

import argparse
import os
import shutil
import pandas as pd
from faker import Faker

# Columns that get replaced with Indian-equivalent fake values
IDENTITY_COLUMNS = ["FIRST", "LAST"]
ADDRESS_COLUMNS = ["ADDRESS", "CITY", "STATE", "ZIP"]

# Columns dropped entirely (see design decision above)
DROPPED_COLUMNS = ["RACE", "ETHNICITY"]

# Files copied through untouched (medical codes are international standards)
CLINICAL_FILES = [
    "conditions.csv",
    "medications.csv",
    "observations.csv",
    "encounters.csv",
    "procedures.csv",
    "immunizations.csv",
    "allergies.csv",
    "careplans.csv",
    "devices.csv",
    "imaging_studies.csv",
    "supplies.csv",
    "payers.csv",
    "payer_transitions.csv",
    "organizations.csv",
    "providers.csv",
]


def indianize_patients(input_path: str, output_path: str, seed: int):
    fake = Faker("en_IN")
    Faker.seed(seed)

    df = pd.read_csv(input_path)

    n = len(df)
    genders = df["GENDER"] if "GENDER" in df.columns else ["M"] * n

    first_names = []
    last_names = []
    addresses = []
    cities = []
    states = []
    zips = []

    for i in range(n):
        gender = genders.iloc[i] if hasattr(genders, "iloc") else genders[i]
        if str(gender).upper().startswith("F"):
            first_names.append(fake.first_name_female())
        else:
            first_names.append(fake.first_name_male())
        last_names.append(fake.last_name())
        addresses.append(fake.street_address())
        cities.append(fake.city())
        states.append(fake.state())
        zips.append(fake.postcode())

    df["FIRST"] = first_names
    df["LAST"] = last_names
    df["ADDRESS"] = addresses
    df["CITY"] = cities
    df["STATE"] = states
    df["ZIP"] = zips

    for col in DROPPED_COLUMNS:
        if col in df.columns:
            df = df.drop(columns=[col])

    df.to_csv(output_path, index=False)
    print(f"  patients.csv -> Indianized {n} records, dropped columns: {DROPPED_COLUMNS}")


def copy_clinical_files(input_dir: str, output_dir: str):
    copied = 0
    for filename in CLINICAL_FILES:
        src = os.path.join(input_dir, filename)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(output_dir, filename))
            copied += 1
    print(f"  Copied {copied} clinical files unchanged.")


def main():
    parser = argparse.ArgumentParser(description="Indianize a Synthea CSV export.")
    parser.add_argument("--input", required=True, help="Path to Synthea's csv output folder")
    parser.add_argument("--output", required=True, help="Path to save Indianized output")
    parser.add_argument("--seed", required=True, type=int, help="Random seed (use the same seed as the Synthea run)")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    patients_src = os.path.join(args.input, "patients.csv")
    patients_dst = os.path.join(args.output, "patients.csv")

    print(f"Indianizing patients.csv from {args.input} ...")
    indianize_patients(patients_src, patients_dst, args.seed)

    print("Copying clinical files unchanged ...")
    copy_clinical_files(args.input, args.output)

    print(f"Done. Indianized data written to: {args.output}")


if __name__ == "__main__":
    main()
