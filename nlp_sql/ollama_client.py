# track_b/ollama_client.py

import os
import requests
from typing import Dict, Any


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_URL = os.getenv("OLLAMA_URL", f"{OLLAMA_BASE_URL}/api/generate")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "qwen2.5-coder")


def check_ollama_status() -> Dict[str, Any]:
    """
    Checks if Ollama daemon is active and whether the target model is available.
    """
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        if response.status_code == 200:
            models_data = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models_data]
            model_available = any(MODEL_NAME in name for name in model_names)
            return {
                "running": True,
                "model_available": model_available,
                "installed_models": model_names,
                "error": None
            }
    except Exception as e:
        return {
            "running": False,
            "model_available": False,
            "installed_models": [],
            "error": str(e)
        }

    return {
        "running": False,
        "model_available": False,
        "installed_models": [],
        "error": "Unexpected response from Ollama"
    }


def _get_mock_fallback_sql(prompt: str) -> str:
    """
    Fallback mock SQL generator for offline testing or machines without Ollama running.
    """
    prompt_lower = prompt.lower()
    if "diabetes" in prompt_lower:
        return (
            "```sql\n"
            "SELECT hospital_id, COUNT(DISTINCT patient_id) AS patient_count\n"
            "FROM conditions\n"
            "WHERE description = 'Diabetes'\n"
            "GROUP BY hospital_id\n"
            "HAVING COUNT(DISTINCT patient_id) >= 5;\n"
            "```"
        )
    elif "metformin" in prompt_lower:
        return (
            "```sql\n"
            "SELECT m.hospital_id, COUNT(DISTINCT m.patient_id) AS patient_count\n"
            "FROM medications AS m\n"
            "WHERE m.description = 'Metformin'\n"
            "GROUP BY m.hospital_id\n"
            "HAVING COUNT(DISTINCT m.patient_id) >= 5;\n"
            "```"
        )
    else:
        return (
            "```sql\n"
            "SELECT hospital_id, COUNT(*) AS patient_count\n"
            "FROM patients\n"
            "GROUP BY hospital_id\n"
            "HAVING COUNT(*) >= 5;\n"
            "```"
        )


def call_ollama(prompt: str) -> str:
    """
    Invokes the local Qwen2.5-Coder model via Ollama's HTTP API.

    Args:
        prompt: Formatted prompt containing schema and user question.

    Returns:
        Generated text response from the model.
    """
    # Check if mock mode is explicitly requested
    if os.getenv("MOCK_OLLAMA", "").lower() in ("true", "1", "yes"):
        return _get_mock_fallback_sql(prompt)

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0
        }
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")
    except requests.exceptions.RequestException as e:
        # If running offline and user hasn't started Ollama, provide clear guidance
        if os.getenv("MOCK_FALLBACK_ON_ERROR", "").lower() in ("true", "1", "yes"):
            return _get_mock_fallback_sql(prompt)

        raise ConnectionError(
            f"Failed to connect to Ollama at '{OLLAMA_URL}'. "
            f"Make sure Ollama is installed and running (`ollama serve`), "
            f"and '{MODEL_NAME}' is pulled (`ollama pull {MODEL_NAME}`). "
            f"To test offline without Ollama, set environment variable MOCK_OLLAMA=true. "
            f"Original error: {e}"
        ) from e