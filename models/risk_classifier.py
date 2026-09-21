def classify_risk(features: dict) -> dict:
    """
    features expected keys (all numeric/bool):
      - result_count: int
      - distinct_sensitive_values: int   (l-diversity count)
      - k_threshold: int (default 5)
      - l_threshold: int (default 2)
      - query_granularity: int  (e.g. how many GROUP BY dimensions)
      - is_single_hospital: bool
    Returns:
      {"k_anon_pass": bool, "l_diversity_pass": bool,
       "disclose": bool, "risk_score": float}
    Logic:
      1. Rule-based k-anon check: result_count >= k_threshold
      2. Rule-based l-diversity check: distinct_sensitive_values >= l_threshold
      3. risk_score comes from the trained RF/LR model (probability of "risky")
      4. disclose = k_anon_pass AND l_diversity_pass  (hard gate — model score is informational)
    """

def process_multivalue_result(values: list[dict], feature_fn) -> list[dict]:
    """
    values: [{"group_key": ..., "raw_value": ..., "features": {...}}, ...]
    feature_fn: function to convert raw item -> feature dict if not precomputed
    For each item: run classify_risk, attach:
      {"disclosed": bool, "value": raw_value or "below disclosure threshold"}
    Returns the full list, order preserved, nothing dropped.
    """