import re
import requests

from app.core.config import settings


def _get_mock_fallback_sql(prompt: str) -> str:
    """
    Returns mock SQL for testing when Ollama is disabled or unavailable.

    The PII case intentionally simulates an LLM returning unsafe SQL.
    The SQL validator is responsible for blocking that SQL.
    """

    prompt_lower = prompt.lower()

    # Simulate an LLM returning unsafe PII SQL.
    if "select" in prompt_lower and any(
        x in prompt_lower
        for x in ["birth_date", "address", "select name"]
    ):
        match = re.search(
            r"select\s+.+",
            prompt,
            re.IGNORECASE
        )

        if match:
            return f"```sql\n{match.group(0)}\n```"

    # Diabetes query
    if "diabet" in prompt_lower:  # catches "diabetes" and "diabetic"
        return """```sql
SELECT COUNT(DISTINCT patient_id) AS patient_count
FROM conditions
WHERE LOWER(condition_desc) LIKE '%diabetes%';
```````"""

    # Hypertension query
    if "hypertens" in prompt_lower or "blood pressure" in prompt_lower:
        return """```sql
SELECT COUNT(DISTINCT patient_id) AS patient_count
FROM conditions
WHERE LOWER(condition_desc) LIKE '%hypertension%';
``````"""

    # Cardiovascular query
    if "cardio" in prompt_lower or "heart" in prompt_lower:
        return """```sql
SELECT COUNT(DISTINCT patient_id) AS patient_count
FROM conditions
WHERE LOWER(condition_desc) LIKE '%cardio%';
`````"""

    # Metformin query
    if "metformin" in prompt_lower:
        return """```sql
SELECT COUNT(DISTINCT patient_id) AS patient_count
FROM medications
WHERE LOWER(drug_name) LIKE '%metformin%';
````"""

    # Default query
    return """```sql
SELECT COUNT(DISTINCT patient_id) AS patient_count
FROM patients;
```"""


def call_ollama(prompt: str) -> str:
    """
    Calls the Ollama local API.

    If MOCK_OLLAMA is enabled, returns mock SQL.
    If Ollama is unavailable, falls back to mock SQL.
    """

    mock_mode = settings.mock_ollama

    # Use mock mode
    if mock_mode:
        return _get_mock_fallback_sql(prompt)

    # Real Ollama API
    url = "http://localhost:11434/api/generate"

    payload = {
        "model": "qwen2.5-coder:1.5b",
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=30
        )

        response.raise_for_status()

        return response.json().get("response", "")

    except Exception as e:
        print(
            f"Ollama connection failed ({e}). "
            "Falling back to mock SQL mode."
        )

        return _get_mock_fallback_sql(prompt)