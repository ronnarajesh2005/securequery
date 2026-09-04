-- Shared schema for Hospital A, B, C — identical structure, isolated data.
-- This file is mounted into each hospital's container separately, so each
-- hospital ends up with its own independent copy of these tables.

CREATE TABLE patients (
    patient_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    date_of_birth   DATE NOT NULL,
    gender          VARCHAR(20),
    zip_code        VARCHAR(10),
    city            VARCHAR(100),
    state           VARCHAR(100),
    created_at      TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE encounters (
    encounter_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID NOT NULL REFERENCES patients(patient_id),
    encounter_date  DATE NOT NULL,
    encounter_type  VARCHAR(100),
    provider        VARCHAR(150),
    reason_code     VARCHAR(50),   -- SNOMED code
    reason_desc     VARCHAR(255),
    created_at      TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE conditions (
    condition_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID NOT NULL REFERENCES patients(patient_id),
    encounter_id    UUID REFERENCES encounters(encounter_id),
    condition_code  VARCHAR(50),   -- SNOMED code
    condition_desc  VARCHAR(255),
    onset_date      DATE,
    resolved_date   DATE,
    created_at      TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE medications (
    medication_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID NOT NULL REFERENCES patients(patient_id),
    encounter_id    UUID REFERENCES encounters(encounter_id),
    drug_code       VARCHAR(50),   -- RxNorm code
    drug_name       VARCHAR(255),
    start_date      DATE,
    end_date        DATE,
    created_at      TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE observations (
    observation_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID NOT NULL REFERENCES patients(patient_id),
    encounter_id    UUID REFERENCES encounters(encounter_id),
    obs_code        VARCHAR(50),   -- LOINC code
    obs_desc        VARCHAR(255),
    obs_value       VARCHAR(255),
    obs_unit        VARCHAR(50),
    obs_date        DATE,
    created_at      TIMESTAMP NOT NULL DEFAULT now()
);

CREATE EXTENSION IF NOT EXISTS "pgcrypto"; -- needed for gen_random_uuid()
