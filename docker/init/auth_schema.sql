CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE researchers (
    researcher_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(150) NOT NULL,
    role            VARCHAR(50) NOT NULL DEFAULT 'researcher',
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE consent_purposes (
    purpose_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    purpose_code    VARCHAR(100) UNIQUE NOT NULL,
    description     VARCHAR(255) NOT NULL
);

CREATE TABLE researcher_permissions (
    permission_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    researcher_id   UUID NOT NULL REFERENCES researchers(researcher_id),
    purpose_id      UUID NOT NULL REFERENCES consent_purposes(purpose_id),
    hospital_scope  VARCHAR(50) NOT NULL DEFAULT 'all', -- 'all' or a specific hospital id
    data_localization_ok BOOLEAN NOT NULL DEFAULT true,
    granted_at      TIMESTAMP NOT NULL DEFAULT now(),
    expires_at      TIMESTAMP
);
