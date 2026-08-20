# SecureQuery — Module Contracts

These function signatures are the integration points between the three
tracks. Internals are up to each person — names, parameters, and return
shapes below must match exactly, since the backend imports these directly.

Any change to a signature here needs a heads-up in the group chat before
it's merged.

---

## Track B — nlp_sql/

```python
def generate_sql(question: str, schema: dict) -> dict:
    """
    Returns: {"sql": str, "raw_llm_output": str}
    """

def validate_sql(sql: str, schema: dict) -> dict:
    """
    Returns: {"valid": bool, "errors": list[str], "sql": str}
    (sql may be rewritten, e.g. LIMIT inserted)
    """

def extract_features(sql: str, schema: dict, count_callback=None) -> dict:
    """
    Returns: {
        "num_filters": int,
        "predicted_result_count": int | None,
        "distinct_sensitive_values": int,
        "single_hospital": bool,
        "attribute_rarity": float
    }
    """
```

---

## Track C — privacy_smpc/

```python
def classify_risk(features: dict) -> dict:
    """
    Returns: {
        "k_anon_pass": bool,
        "l_diversity_pass": bool,
        "disclose": bool,
        "risk_score": float
    }
    """

def secret_share(value, num_parties: int) -> list:
    """
    Returns: list of shares, one per hospital
    """

def aggregate_shares(shares_by_hospital: dict) -> float | int:
    """
    shares_by_hospital: {hospital_id: share}
    Returns: the reconstructed aggregate
    """

def process_multivalue_result(values: list[dict], feature_fn) -> list[dict]:
    """
    values: list of {"group_key": ..., "raw_value": ..., "features": {...}}
    Returns: same list, each item annotated with
        {"disclosed": bool, "value": <real or masked placeholder>}
    """

def build_analytics(results: list[dict]) -> dict:
    """
    Returns: {"stats": {...}, "charts": [...], "tables": [...]}
    """
```

---

## Track A — backend/ (orchestration, owned by integrator)

Calls the above in this order per query:

`generate_sql` → `validate_sql` → DPDP check → `extract_features` →
`classify_risk` → dispatch to hospitals → `secret_share` /
`aggregate_shares` (skipped if single-hospital) →
`process_multivalue_result` → `build_analytics` → audit log write →
response to researcher
