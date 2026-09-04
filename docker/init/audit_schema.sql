CREATE TABLE audit_log (
    entry_id        BIGSERIAL PRIMARY KEY,
    researcher_id   UUID NOT NULL,
    query_text      TEXT NOT NULL,
    generated_sql   TEXT,
    dpdp_check_result   VARCHAR(50),
    risk_check_result   VARCHAR(50),
    disclosed       BOOLEAN,
    entry_data      TEXT NOT NULL,   -- human-readable serialized entry
    entry_hash      VARCHAR(64) NOT NULL,  -- SHA-256 of (entry_data + prev_hash)
    prev_hash       VARCHAR(64),
    created_at      TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_researcher ON audit_log(researcher_id);
CREATE INDEX idx_audit_created_at ON audit_log(created_at);
