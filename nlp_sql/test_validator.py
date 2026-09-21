# track_b/tests/test_validator.py

import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from sql_validator import validate_sql
from schemas.mock_schema import SCHEMA


def test_valid_aggregate_query():
    """
    Test that a valid aggregated query with GROUP BY and HAVING passes validation.
    """
    sql = """
        SELECT hospital_id, COUNT(*) AS patient_count
        FROM conditions
        WHERE description = 'Diabetes'
        GROUP BY hospital_id
        HAVING COUNT(*) >= 5
    """
    result = validate_sql(sql, SCHEMA)
    print("\nValid query result:", result)
    assert result["valid"] is True
    assert len(result["errors"]) == 0
    assert "patient_count" in result["sql"]


def test_empty_sql():
    """
    Test that empty or whitespace-only SQL queries are rejected.
    """
    res1 = validate_sql("", SCHEMA)
    assert res1["valid"] is False
    assert any("empty" in err.lower() for err in res1["errors"])

    res2 = validate_sql("   \n  \t ", SCHEMA)
    assert res2["valid"] is False
    assert any("empty" in err.lower() for err in res2["errors"])


def test_syntax_error():
    """
    Test that syntactically malformed SQL is rejected.
    """
    bad_sql = "SELECT FROM WHERE patients"
    result = validate_sql(bad_sql, SCHEMA)
    assert result["valid"] is False
    assert any("syntax" in err.lower() for err in result["errors"])


def test_forbidden_operations():
    """
    Test that non-SELECT and DDL/DML statements are strictly rejected.
    """
    forbidden_queries = [
        "DROP TABLE patients",
        "DELETE FROM conditions WHERE id = 1",
        "INSERT INTO patients (id, gender) VALUES (1, 'M')",
        "UPDATE patients SET gender = 'F' WHERE id = 1",
        "ALTER TABLE patients ADD COLUMN ssn text",
        "TRUNCATE TABLE observations",
        "GRANT SELECT ON patients TO PUBLIC"
    ]

    for sql in forbidden_queries:
        result = validate_sql(sql, SCHEMA)
        assert result["valid"] is False, f"Expected {sql} to fail validation"
        assert len(result["errors"]) > 0


def test_unknown_table():
    """
    Test that queries referencing non-existent tables are rejected.
    """
    sql = "SELECT id FROM non_existent_table"
    result = validate_sql(sql, SCHEMA)
    assert result["valid"] is False
    assert any("unknown table" in err.lower() for err in result["errors"])


def test_unknown_column():
    """
    Test that queries referencing non-existent columns are rejected.
    """
    sql = "SELECT non_existent_column FROM patients"
    result = validate_sql(sql, SCHEMA)
    assert result["valid"] is False
    assert any("unknown column" in err.lower() for err in result["errors"])


def test_pii_rejection_standard_names():
    """
    Test that direct selection of PII columns (e.g. name, email, phone, SSN) is rejected.
    """
    pii_queries = [
        "SELECT name FROM patients",
        "SELECT first_name, last_name FROM patients",
        "SELECT ssn FROM patients",
        "SELECT email FROM patients",
        "SELECT phone FROM patients",
        "SELECT national_id FROM patients"
    ]

    for sql in pii_queries:
        result = validate_sql(sql, SCHEMA)
        assert result["valid"] is False, f"Expected PII query '{sql}' to be rejected"
        assert any("pii" in err.lower() for err in result["errors"])


def test_pii_rejection_custom_schema_flag():
    """
    Test that columns marked with 'pii': True in the schema are rejected.
    """
    custom_schema = {
        "patients": {
            "columns": {
                "id": {"type": "integer", "pii": False},
                "medical_record_number": {"type": "string", "pii": True}
            }
        }
    }
    sql = "SELECT medical_record_number FROM patients"
    result = validate_sql(sql, custom_schema)
    assert result["valid"] is False
    assert any("pii" in err.lower() for err in result["errors"])


def test_group_by_guardrail():
    """
    Test that queries with GROUP BY without HAVING minimum group size are rejected,
    while those with HAVING COUNT(*) >= 5 pass.
    """
    # Missing HAVING guardrail
    unsafe_group_by = """
        SELECT hospital_id, COUNT(*)
        FROM conditions
        GROUP BY hospital_id
    """
    res_unsafe = validate_sql(unsafe_group_by, SCHEMA)
    assert res_unsafe["valid"] is False
    assert any("group-size" in err.lower() for err in res_unsafe["errors"])

    # Compliant with HAVING guardrail
    safe_group_by = """
        SELECT hospital_id, COUNT(*)
        FROM conditions
        GROUP BY hospital_id
        HAVING COUNT(*) >= 5
    """
    res_safe = validate_sql(safe_group_by, SCHEMA)
    assert res_safe["valid"] is True


def test_limit_enforcement():
    """
    Test that non-aggregate queries have LIMIT inserted or capped to DEFAULT_LIMIT (100).
    """
    # No limit provided -> inserted
    no_limit_sql = "SELECT id FROM patients"
    res_inserted = validate_sql(no_limit_sql, SCHEMA)
    assert res_inserted["valid"] is True
    assert "LIMIT 100" in res_inserted["sql"]

    # Excessive limit provided -> capped
    excess_limit_sql = "SELECT id FROM patients LIMIT 500"
    res_capped = validate_sql(excess_limit_sql, SCHEMA)
    assert res_capped["valid"] is True
    assert "LIMIT 100" in res_capped["sql"]
    assert "500" not in res_capped["sql"]

    # Safe limit preserved
    safe_limit_sql = "SELECT id FROM patients LIMIT 25"
    res_safe = validate_sql(safe_limit_sql, SCHEMA)
    assert res_safe["valid"] is True
    assert "LIMIT 25" in res_safe["sql"]


def test_aliases_handling():
    """
    Test that column aliases and CTEs are not misidentified as unknown schema elements.
    """
    alias_sql = """
        SELECT hospital_id, COUNT(*) AS patient_count
        FROM conditions
        GROUP BY hospital_id
        HAVING COUNT(*) >= 5
        ORDER BY patient_count DESC
    """
    res = validate_sql(alias_sql, SCHEMA)
    assert res["valid"] is True
    assert len(res["errors"]) == 0


if __name__ == "__main__":
    test_valid_aggregate_query()
    test_empty_sql()
    test_syntax_error()
    test_forbidden_operations()
    test_unknown_table()
    test_unknown_column()
    test_pii_rejection_standard_names()
    test_pii_rejection_custom_schema_flag()
    test_group_by_guardrail()
    test_limit_enforcement()
    test_aliases_handling()

    print("\nAll SQL validator tests passed successfully!")
