import joblib
import os
import pandas as pd

# Load trained models once, at import time
_MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
rf_model = joblib.load(os.path.join(_MODEL_DIR, "rf_model.joblib"))
lr_model = joblib.load(os.path.join(_MODEL_DIR, "lr_model.joblib"))

FEATURE_ORDER = ["result_count", "distinct_sensitive_values", "query_granularity", "is_single_hospital"]


def classify_risk(features: dict) -> dict:
    """
    features expected keys:
      - result_count: int
      - distinct_sensitive_values: int
      - query_granularity: int (optional, default 1)
      - is_single_hospital: bool/int (optional, default 0)
      - k_threshold: int (optional, default 5)
      - l_threshold: int (optional, default 2)
    """
    result_count = features["result_count"]
    distinct_sensitive_values = features["distinct_sensitive_values"]
    query_granularity = features.get("query_granularity", 1)
    is_single_hospital = int(features.get("is_single_hospital", 0))
    k_threshold = features.get("k_threshold", 5)
    l_threshold = features.get("l_threshold", 2)

    # Stage 1: k-anonymity (hard rule)
    k_anon_pass = result_count >= k_threshold

    # Stage 2: l-diversity (hard rule)
    l_diversity_pass = distinct_sensitive_values >= l_threshold

    # ML model gives a risk score (probability the result is "safe"/label=1)
    X = pd.DataFrame([[result_count, distinct_sensitive_values, query_granularity, is_single_hospital]],
                      columns=FEATURE_ORDER)
    risk_score = float(rf_model.predict_proba(X)[0][1])  # probability of class 1 (safe)

    # Hard gate: disclose only if BOTH rule-based checks pass
    disclose = bool(k_anon_pass and l_diversity_pass)

    return {
        "k_anon_pass": k_anon_pass,
        "l_diversity_pass": l_diversity_pass,
        "disclose": disclose,
        "risk_score": round(risk_score, 4)
    }
def process_multivalue_result(values: list, feature_fn=None) -> list:
    """
    values: list of dicts, each like:
      {"group_key": ..., "raw_value": ..., "features": {...}}
    feature_fn: optional function(item) -> dict, used to build features
                if "features" isn't already provided in the item
    Returns the same list, each item annotated with:
      {"disclosed": bool, "value": <real value or masked placeholder>}
    Nothing is dropped — failing items are masked, not removed.
    """
    results = []
    for item in values:
        features = item.get("features")
        if features is None and feature_fn is not None:
            features = feature_fn(item)
        if features is None:
            raise ValueError(f"No features found or derivable for item: {item.get('group_key')}")

        risk_result = classify_risk(features)

        annotated = dict(item)  # copy so we don't mutate the input
        annotated["disclosed"] = risk_result["disclose"]
        annotated["value"] = item["raw_value"] if risk_result["disclose"] else "below disclosure threshold"
        annotated["risk_details"] = risk_result  # useful for debugging/audit trail
        results.append(annotated)

    return results


if __name__ == "__main__":
    # Quick manual test — classify_risk
    print(classify_risk({"result_count": 12, "distinct_sensitive_values": 3}))
    print(classify_risk({"result_count": 2, "distinct_sensitive_values": 3}))
    print(classify_risk({"result_count": 50, "distinct_sensitive_values": 1}))

    # Quick manual test — process_multivalue_result
    mock_values = [
        {"group_key": "H1-2023", "raw_value": 42, "features": {"result_count": 42, "distinct_sensitive_values": 4}},
        {"group_key": "H2-2023", "raw_value": 3, "features": {"result_count": 3, "distinct_sensitive_values": 4}},
        {"group_key": "H3-2023", "raw_value": 80, "features": {"result_count": 80, "distinct_sensitive_values": 1}},
        {"group_key": "H1-2024", "raw_value": 15, "features": {"result_count": 15, "distinct_sensitive_values": 3}},
    ]
    processed = process_multivalue_result(mock_values)
    print("\nMulti-value results:")
    for item in processed:
        print(item)