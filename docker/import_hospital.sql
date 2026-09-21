BEGIN;

-- =========================================================
-- 1. Staging tables
-- =========================================================

DROP TABLE IF EXISTS stg_patients;
DROP TABLE IF EXISTS stg_encounters;
DROP TABLE IF EXISTS stg_conditions;
DROP TABLE IF EXISTS stg_medications;
DROP TABLE IF EXISTS stg_observations;

CREATE TABLE stg_patients (
    "Id" UUID,
    "BIRTHDATE" DATE,
    "DEATHDATE" DATE,
    "SSN" TEXT,
    "DRIVERS" TEXT,
    "PASSPORT" TEXT,
    "PREFIX" TEXT,
    "FIRST" TEXT,
    "MIDDLE" TEXT,
    "LAST" TEXT,
    "SUFFIX" TEXT,
    "MAIDEN" TEXT,
    "MARITAL" TEXT,
    "RACE" TEXT,
    "ETHNICITY" TEXT,
    "GENDER" TEXT,
    "BIRTHPLACE" TEXT,
    "ADDRESS" TEXT,
    "CITY" TEXT,
    "STATE" TEXT,
    "COUNTY" TEXT,
    "FIPS" TEXT,
    "ZIP" TEXT,
    "LAT" DOUBLE PRECISION,
    "LON" DOUBLE PRECISION,
    "HEALTHCARE_EXPENSES" NUMERIC,
    "HEALTHCARE_COVERAGE" NUMERIC,
    "INCOME" NUMERIC
);

CREATE TABLE stg_encounters (
    "Id" UUID,
    "START" TIMESTAMP,
    "STOP" TIMESTAMP,
    "PATIENT" UUID,
    "ORGANIZATION" TEXT,
    "PROVIDER" TEXT,
    "PAYER" TEXT,
    "ENCOUNTERCLASS" TEXT,
    "CODE" TEXT,
    "DESCRIPTION" TEXT,
    "BASE_ENCOUNTER_COST" NUMERIC,
    "TOTAL_CLAIM_COST" NUMERIC,
    "PAYER_COVERAGE" NUMERIC,
    "REASONCODE" TEXT,
    "REASONDESCRIPTION" TEXT
);

CREATE TABLE stg_conditions (
    "START" TIMESTAMP,
    "STOP" TIMESTAMP,
    "PATIENT" UUID,
    "ENCOUNTER" UUID,
    "SYSTEM" TEXT,
    "CODE" TEXT,
    "DESCRIPTION" TEXT
);

CREATE TABLE stg_medications (
    "START" TIMESTAMP,
    "STOP" TIMESTAMP,
    "PATIENT" UUID,
    "PAYER" TEXT,
    "ENCOUNTER" UUID,
    "CODE" TEXT,
    "DESCRIPTION" TEXT,
    "BASE_COST" NUMERIC,
    "PAYER_COVERAGE" NUMERIC,
    "DISPENSES" NUMERIC,
    "TOTALCOST" NUMERIC,
    "REASONCODE" TEXT,
    "REASONDESCRIPTION" TEXT
);

CREATE TABLE stg_observations (
    "DATE" TIMESTAMP,
    "PATIENT" UUID,
    "ENCOUNTER" UUID,
    "CATEGORY" TEXT,
    "CODE" TEXT,
    "DESCRIPTION" TEXT,
    "VALUE" TEXT,
    "UNITS" TEXT,
    "TYPE" TEXT
);

-- =========================================================
-- 2. Load raw Synthea CSVs
-- =========================================================

\copy stg_patients FROM '/tmp/patients.csv' WITH (FORMAT csv, HEADER true);

\copy stg_encounters FROM '/tmp/encounters.csv' WITH (FORMAT csv, HEADER true);

\copy stg_conditions FROM '/tmp/conditions.csv' WITH (FORMAT csv, HEADER true);

\copy stg_medications FROM '/tmp/medications.csv' WITH (FORMAT csv, HEADER true);

\copy stg_observations FROM '/tmp/observations.csv' WITH (FORMAT csv, HEADER true);

-- =========================================================
-- 3. Insert patients
-- Preserve Synthea's UUID
-- =========================================================

INSERT INTO patients (
    patient_id,
    first_name,
    last_name,
    date_of_birth,
    gender,
    zip_code,
    city,
    state
)
SELECT
    "Id",
    "FIRST",
    "LAST",
    "BIRTHDATE",
    "GENDER",
    "ZIP",
    "CITY",
    "STATE"
FROM stg_patients;

-- =========================================================
-- 4. Insert encounters
-- Preserve Synthea's encounter UUID
-- =========================================================

INSERT INTO encounters (
    encounter_id,
    patient_id,
    encounter_date,
    encounter_type,
    provider,
    reason_code,
    reason_desc
)
SELECT
    "Id",
    "PATIENT",
    "START"::date,
    "ENCOUNTERCLASS",
    "PROVIDER",
    "REASONCODE",
    "REASONDESCRIPTION"
FROM stg_encounters;

-- =========================================================
-- 5. Insert conditions
-- =========================================================

INSERT INTO conditions (
    patient_id,
    encounter_id,
    condition_code,
    condition_desc,
    onset_date,
    resolved_date
)
SELECT
    "PATIENT",
    "ENCOUNTER",
    "CODE",
    "DESCRIPTION",
    "START"::date,
    "STOP"::date
FROM stg_conditions;

-- =========================================================
-- 6. Insert medications
-- =========================================================

INSERT INTO medications (
    patient_id,
    encounter_id,
    drug_code,
    drug_name,
    start_date,
    end_date
)
SELECT
    "PATIENT",
    "ENCOUNTER",
    "CODE",
    "DESCRIPTION",
    "START"::date,
    "STOP"::date
FROM stg_medications;

-- =========================================================
-- 7. Insert observations
-- =========================================================

INSERT INTO observations (
    patient_id,
    encounter_id,
    obs_code,
    obs_desc,
    obs_value,
    obs_unit,
    obs_date
)
SELECT
    "PATIENT",
    "ENCOUNTER",
    "CODE",
    "DESCRIPTION",
    "VALUE",
    "UNITS",
    "DATE"::date
FROM stg_observations;

COMMIT;

-- =========================================================
-- 8. Row-count verification
-- =========================================================

SELECT 'patients' AS table_name, COUNT(*) AS row_count FROM patients
UNION ALL
SELECT 'encounters', COUNT(*) FROM encounters
UNION ALL
SELECT 'conditions', COUNT(*) FROM conditions
UNION ALL
SELECT 'medications', COUNT(*) FROM medications
UNION ALL
SELECT 'observations', COUNT(*) FROM observations;