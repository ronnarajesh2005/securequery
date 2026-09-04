import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from feature_extractor import extract_features


def mock_count_callback(sql):
    """
    Mock database COUNT callback.

    In the real system, Team Member 3 / integration layer
    will provide the actual database count.
    """
    return 25


def test_basic_feature_extraction():
    """
    Test a normal multi-hospital query.
    """

    sql = """
        SELECT hospital_id, COUNT(*) AS patient_count
        FROM conditions
        WHERE description = 'Diabetes'
        GROUP BY hospital_id
        HAVING COUNT(*) >= 5
    """

    schema = {
        "patients": {
            "columns": {
                "id": {"type": "integer", "pii": False},
                "hospital_id": {"type": "string", "pii": False}
            }
        },
        "conditions": {
            "columns": {
                "patient_id": {"type": "integer", "pii": False},
                "description": {"type": "string", "pii": False},
                "hospital_id": {"type": "string", "pii": False}
            }
        }
    }

    features = extract_features(
        sql,
        schema,
        count_callback=mock_count_callback
    )

    print("\nFeatures:")
    print(features)

    assert isinstance(features, dict)

    assert "num_filters" in features
    assert "predicted_result_count" in features
    assert "distinct_sensitive_values" in features
    assert "single_hospital" in features
    assert "attribute_rarity" in features

    assert features["predicted_result_count"] == 25

    assert features["num_filters"] >= 1

    assert features["single_hospital"] is False

    assert 0 <= features["attribute_rarity"] <= 1


def test_single_hospital_query():
    """
    Test a query restricted to one hospital.
    """

    sql = """
        SELECT COUNT(*)
        FROM conditions
        WHERE description = 'Diabetes'
        AND hospital_id = 'H001'
    """

    schema = {
        "conditions": {
            "columns": {
                "description": {
                    "type": "string",
                    "pii": False
                },
                "hospital_id": {
                    "type": "string",
                    "pii": False
                }
            }
        }
    }

    features = extract_features(
        sql,
        schema,
        count_callback=mock_count_callback
    )

    print("\nSingle hospital features:")
    print(features)

    assert features["predicted_result_count"] == 25

    assert features["num_filters"] >= 2

    assert features["single_hospital"] is True


def test_query_without_filters():
    """
    Test a query that has no WHERE conditions.
    """

    sql = """
        SELECT hospital_id, COUNT(*)
        FROM patients
        GROUP BY hospital_id
    """

    schema = {
        "patients": {
            "columns": {
                "hospital_id": {
                    "type": "string",
                    "pii": False
                }
            }
        }
    }

    features = extract_features(
        sql,
        schema,
        count_callback=mock_count_callback
    )

    print("\nNo-filter features:")
    print(features)

    assert features["num_filters"] == 0

    assert features["predicted_result_count"] == 25

    assert features["single_hospital"] is False


def test_count_callback_not_provided():
    """
    Test that predicted_result_count becomes None
    when no database callback is provided.
    """

    sql = """
        SELECT COUNT(*)
        FROM patients
        WHERE gender = 'F'
    """

    schema = {
        "patients": {
            "columns": {
                "gender": {
                    "type": "string",
                    "pii": False
                }
            }
        }
    }

    features = extract_features(
        sql,
        schema
    )

    print("\nFeatures without callback:")
    print(features)

    assert features["predicted_result_count"] is None

    assert features["num_filters"] >= 1


def test_multiple_filters():
    """
    Test a query containing multiple WHERE conditions.
    """

    sql = """
        SELECT COUNT(*)
        FROM patients
        WHERE gender = 'F'
        AND hospital_id = 'H001'
        AND birth_date > '1980-01-01'
    """

    schema = {
        "patients": {
            "columns": {
                "gender": {
                    "type": "string",
                    "pii": False
                },
                "hospital_id": {
                    "type": "string",
                    "pii": False
                },
                "birth_date": {
                    "type": "date",
                    "pii": False
                }
            }
        }
    }

    features = extract_features(
        sql,
        schema,
        count_callback=mock_count_callback
    )

    print("\nMultiple-filter features:")
    print(features)

    assert features["num_filters"] >= 3

    assert features["single_hospital"] is True

    assert features["predicted_result_count"] == 25


if __name__ == "__main__":
    test_basic_feature_extraction()
    test_single_hospital_query()
    test_query_without_filters()
    test_count_callback_not_provided()
    test_multiple_filters()

    print("\nAll feature extraction tests passed!")