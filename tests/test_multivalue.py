import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.risk_pipeline import process_multivalue_result


def test_mixed_pass_fail_all_returned():
    values = [
        {"group_key": "A", "raw_value": 42, "features": {"result_count": 42, "distinct_sensitive_values": 4}},
        {"group_key": "B", "raw_value": 3, "features": {"result_count": 3, "distinct_sensitive_values": 4}},
    ]
    result = process_multivalue_result(values)
    assert len(result) == 2  # nothing dropped


def test_failed_items_are_masked():
    values = [{"group_key": "B", "raw_value": 3, "features": {"result_count": 3, "distinct_sensitive_values": 4}}]
    result = process_multivalue_result(values)
    assert result[0]["disclosed"] is False
    assert result[0]["value"] == "below disclosure threshold"


def test_passed_items_show_real_value():
    values = [{"group_key": "A", "raw_value": 42, "features": {"result_count": 42, "distinct_sensitive_values": 4}}]
    result = process_multivalue_result(values)
    assert result[0]["disclosed"] is True
    assert result[0]["value"] == 42


def test_empty_input_returns_empty_list():
    assert process_multivalue_result([]) == []