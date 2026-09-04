# SecureQuery — Risk Classification, SMPC & Analytics Module

This module implements the **privacy risk classification**, **secure multi-party
computation (SMPC)**, and **analytics/visualization** layer of SecureQuery — a
system that lets researchers query aggregated healthcare data across multiple
hospitals without exposing individual patient records or violating anonymity
thresholds.

This module is standalone and tested against mocked feature vectors and mocked
hospital result sets. It is not responsible for authentication, SQL generation,
or the API layer — those are handled by other modules in the system.

## Technologies used

| Component | Technology |
|---|---|
| Risk classifier | scikit-learn (RandomForestClassifier + LogisticRegression) |
| SMPC | Custom Shamir's Secret Sharing implementation (pure Python, no external crypto library — chosen for transparency and to avoid a black-box dependency) |
| Data handling | pandas, numpy |
| Analytics/visualization | matplotlib |
| Testing | pytest |
| Model persistence | joblib |

## Project structure

```
securequery-risk-smpc/
├── data/
│   ├── generate_synthetic_data.py   # generates labeled training data
│   └── synthetic_risk_data.csv
├── models/
│   ├── train_models.py              # trains and saves RF + LR models
│   ├── rf_model.joblib
│   └── lr_model.joblib
├── core/
│   └── risk_pipeline.py             # classify_risk(), process_multivalue_result()
├── smpc/
│   └── shamir.py                    # secret_share(), aggregate_shares()
├── analytics/
│   └── analytics.py                 # build_analytics()
├── tests/
│   ├── test_risk_classifier.py
│   ├── test_shamir.py
│   ├── test_multivalue.py
│   └── test_analytics.py
└── README.md
```

## Setup

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install scikit-learn pandas numpy matplotlib joblib pytest

python data\generate_synthetic_data.py    # generates training data
python models\train_models.py             # trains and saves models
python -m pytest tests\ -v                 # runs all unit tests
```

## Function contracts, with example input/output

### 1. `classify_risk(features: dict) -> dict`

Two-stage privacy check: k-anonymity (result count ≥ k) and l-diversity
(≥ l distinct sensitive-attribute values). Both must pass for disclosure.
A trained Random Forest additionally provides a `risk_score`, but disclosure
is always gated by the hard rule-based checks, not the model score — this
avoids relying on the ML model alone for a privacy-critical decision.

```python
>>> classify_risk({"result_count": 20, "distinct_sensitive_values": 4})
{'k_anon_pass': True, 'l_diversity_pass': True, 'disclose': True, 'risk_score': 0.53}

>>> classify_risk({"result_count": 3, "distinct_sensitive_values": 4})
{'k_anon_pass': False, 'l_diversity_pass': True, 'disclose': False, 'risk_score': 0.02}

>>> classify_risk({"result_count": 100, "distinct_sensitive_values": 1})
{'k_anon_pass': True, 'l_diversity_pass': False, 'disclose': False, 'risk_score': 0.0}
```

### 2. `secret_share(value, num_parties) -> list`

Splits a value into shares using Shamir's Secret Sharing over a finite field
(prime modulus). No individual share reveals the original value.

```python
>>> secret_share(42, num_parties=3)
[(1, 1187839273465), (2, 2375678546888), (3, 3563517820311)]  # values vary — random each run
```

### 3. `aggregate_shares(shares_by_hospital) -> float | int`

Reconstructs the **sum** of multiple hospitals' secret-shared values via
Lagrange interpolation, without any hospital revealing its raw value to
another. This is the core SMPC guarantee.

```python
>>> hospital_values = {"H1": 120, "H2": 95, "H3": 60}
>>> # each hospital secret-shares its value, shares are combined position-wise
>>> aggregate_shares(combined_shares)
275   # == 120 + 95 + 60, reconstructed without exposing individual values
```

### 4. `process_multivalue_result(values, feature_fn) -> list[dict]`

Runs the risk classifier on each item in a breakdown (e.g. hospital-wise or
year-wise counts) independently. Passing items are disclosed as-is; failing
items are masked. Nothing is dropped from the response.

```python
>>> values = [
...     {"group_key": "H1-2023", "raw_value": 42, "features": {"result_count": 42, "distinct_sensitive_values": 4}},
...     {"group_key": "H2-2023", "raw_value": 3,  "features": {"result_count": 3,  "distinct_sensitive_values": 4}},
... ]
>>> process_multivalue_result(values)
[
  {'group_key': 'H1-2023', 'raw_value': 42, ..., 'disclosed': True,  'value': 42},
  {'group_key': 'H2-2023', 'raw_value': 3,  ..., 'disclosed': False, 'value': 'below disclosure threshold'}
]
```

### 5. `build_analytics(results) -> dict`

Takes a final, post-risk-check disclosed result set and produces descriptive
stats, comparison tables, and chart-ready matplotlib figures.

```python
>>> results = [
...     {"hospital": "H1", "year": 2023, "disease": "Diabetes", "value": 120},
...     {"hospital": "H2", "year": 2023, "disease": "Diabetes", "value": 95},
... ]
>>> output = build_analytics(results)
>>> output["stats"]
{'count': 2, 'avg': 107.5, 'min': 95, 'max': 120}
>>> output["tables"][0]
{'title': 'Cross-hospital comparison', 'data': [{'hospital': 'H1', 'total': 120}, {'hospital': 'H2', 'total': 95}]}
>>> [c["title"] for c in output["charts"]]
['Cross-hospital comparison', 'Disease distribution', 'Year-over-year trend']
```

## Design decisions

- **Disclosure is always hard-gated by k-anonymity and l-diversity rules**,
  not the ML model. The Random Forest's `risk_score` is informational —
  useful for audit trails and the RF vs LR comparison — but never overrides
  the rule-based check. This avoids a scenario where a probabilistic model
  incorrectly allows a re-identifiable result through.
- **Shamir's Secret Sharing was implemented from scratch** rather than using
  a library like PyCryptodome, to keep the cryptographic logic transparent
  and explainable, and to demonstrate the additive homomorphic property
  (shares from different secrets can be summed position-wise before
  reconstruction) directly in code.
- **`process_multivalue_result` never drops failing items** — it masks them
  in place, so the caller (API layer) always gets a complete, well-formed
  response even when some values are suppressed for privacy.

## Testing

All functions have unit tests in `tests/`, covering boundary cases (exact
k/l thresholds), the actual privacy property of secret sharing (shares don't
reveal the original value), multi-hospital summation correctness, and
analytics output correctness against manually computed expected values.

```
python -m pytest tests\ -v
```