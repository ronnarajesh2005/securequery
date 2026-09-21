import os
import requests

def call_ollama(prompt: str) -> str:
    """
    Calls the Ollama local API. If MOCK_OLLAMA is set or Ollama is offline,
    returns context-aware mock SQL queries for testing.
    """
    mock_mode = os.getenv("MOCK_OLLAMA", "true").lower() in ("true", "1", "yes")

    if mock_mode:
        prompt_lower = prompt.lower()
        if "diabetes" in prompt_lower:
            return """```sql
SELECT COUNT(DISTINCT patient_id) AS patient_count
FROM conditions
WHERE LOWER(condition_desc) LIKE '%diabetes%';
```"""
        else:
            return """```sql
SELECT COUNT(DISTINCT patient_id) AS patient_count
FROM patients;
```"""

    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "qwen2.5-coder",
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as e:
        print(f"Ollama connection failed ({e}). Falling back to mock SQL mode.")
        prompt_lower = prompt.lower()
        if "diabetes" in prompt_lower:
            return """```sql
SELECT COUNT(DISTINCT patient_id) AS patient_count
FROM conditions
WHERE LOWER(condition_desc) LIKE '%diabetes%';
```"""
        return """```sql
SELECT COUNT(DISTINCT patient_id) AS patient_count
FROM patients;
```"""