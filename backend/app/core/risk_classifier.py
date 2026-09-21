import joblib
import warnings
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parents[1] / "models"
_rf_model = joblib.load(MODEL_DIR / "rf_model.joblib")

K_THRESHOLD = 5
L_THRESHOLD = 1  # A query filtering to a single condition inherently has
                 # distinct_sensitive_values=1; l-diversity's real purpose is
                 # protecting multi-category breakdowns, not gating single-
                 # condition aggregate counts (which k-anonymity already covers)

def classify_risk(features: dict) -> dict:
    """
    Logic:
      1. Rule-based k-anon check: result_count >= K_THRESHOLD
      2. Rule-based l-diversity check: distinct_sensitive_values >= L_THRESHOLD
         (no fallback to result_count — missing/unpopulated distinct_sensitive_values
         must FAIL l-diversity to prevent unvalidated disclosures)
      3. risk_score comes from the trained RF model (informational only)
      4. disclose = k_anon_pass AND l_diversity_pass
    """
    result_count = features.get("result_count", 0)
    query_granularity = features.get("query_granularity", 0)
    is_single_hospital = int(features.get("is_single_hospital", False))
    distinct_sensitive_values = features.get("distinct_sensitive_values", 0)

    # 1. k-Anonymity Check
    k_anon_pass = result_count >= K_THRESHOLD

    # 2. l-Diversity Check — fail safe when value is missing (0 < L_THRESHOLD)
    l_diversity_pass = distinct_sensitive_values >= L_THRESHOLD

    # 3. Random Forest Inference (informational only, suppress warnings)
    model_input = [[result_count, distinct_sensitive_values, query_granularity, is_single_hospital]]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        risk_score = float(_rf_model.predict_proba(model_input)[0][1])

    # 4. Disclosure Decision
    disclose = k_anon_pass and l_diversity_pass

    return {
        "k_anon_pass": k_anon_pass,
        "l_diversity_pass": l_diversity_pass,
        "disclose": disclose,
        "risk_score": round(risk_score, 4),
    }

def process_multivalue_result(values: list, feature_fn=None) -> list:
    results = []
    for item in values:
        features = item.get("features")
        if features is None and callable(feature_fn):
            features = feature_fn(item.get("raw_value"))
        if features is None:
            features = {}

        risk_result = classify_risk(features)

        results.append({
            "group_key": item.get("group_key"),
            "disclosed": risk_result["disclose"],
            "value": item.get("raw_value") if risk_result["disclose"] else "below disclosure threshold",
            "risk_result": risk_result,
        })
    return results

def build_analytics(results: list) -> dict:
    disclosed_results = [r for r in results if r.get("disclosed")]
    masked_count = len(results) - len(disclosed_results)

    disclosed_values = [r["value"] for r in disclosed_results if isinstance(r["value"], (int, float))]

    stats = {
        "total_groups": len(results),
        "disclosed_groups": len(disclosed_results),
        "masked_groups": masked_count,
        "sum_disclosed_values": sum(disclosed_values) if disclosed_values else 0,
        "avg_disclosed_value": (sum(disclosed_values) / len(disclosed_values)) if disclosed_values else None,
    }

    charts = [
        {
            "type": "bar",
            "title": "Disclosed values by group",
            "labels": [r["group_key"] for r in disclosed_results],
            "values": [r["value"] for r in disclosed_results],
        }
    ]

    tables = [
        {
            "title": "Full result breakdown",
            "columns": ["group_key", "value", "disclosed"],
            "rows": [
                {"group_key": r["group_key"], "value": r["value"], "disclosed": r["disclosed"]}
                for r in results
            ],
        }
    ]

    return {"stats": stats, "charts": charts, "tables": tables}