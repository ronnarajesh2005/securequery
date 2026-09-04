import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.risk_pipeline import classify_risk


def test_k_anon_fail_below_threshold():
    result = classify_risk({"result_count": 3, "distinct_sensitive_values": 5})
    assert result["k_anon_pass"] is False
    assert result["disclose"] is False


def test_k_anon_pass_at_exact_threshold():
    result = classify_risk({"result_count": 5, "distinct_sensitive_values": 5})
    assert result["k_anon_pass"] is True


def test_l_diversity_fail_single_value():
    result = classify_risk({"result_count": 50, "distinct_sensitive_values": 1})
    assert result["l_diversity_pass"] is False
    assert result["disclose"] is False


def test_disclose_requires_both_stages():
    # passes k-anon but fails l-diversity -> must not disclose
    result = classify_risk({"result_count": 100, "distinct_sensitive_values": 1})
    assert result["k_anon_pass"] is True
    assert result["l_diversity_pass"] is False
    assert result["disclose"] is False


def test_disclose_true_when_both_pass():
    result = classify_risk({"result_count": 20, "distinct_sensitive_values": 4})
    assert result["disclose"] is True


def test_risk_score_in_valid_range():
    result = classify_risk({"result_count": 20, "distinct_sensitive_values": 4})
    assert 0.0 <= result["risk_score"] <= 1.0


def test_output_schema():
    result = classify_risk({"result_count": 20, "distinct_sensitive_values": 4})
    assert set(result.keys()) == {"k_anon_pass", "l_diversity_pass", "disclose", "risk_score"}