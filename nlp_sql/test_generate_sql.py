# track_b/tests/test_generate_sql.py

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from prompt_builder import build_prompt
from pipeline import clean_sql_output, generate_sql
from ollama_client import call_ollama
from schemas.mock_schema import SCHEMA


def test_build_prompt():
    """
    Test that build_prompt correctly formats the schema, rules, and question.
    """
    question = "How many diabetes patients per hospital in 2024?"
    prompt = build_prompt(question, SCHEMA)

    assert isinstance(prompt, str)
    assert question in prompt
    assert "TABLE: patients" in prompt
    assert "TABLE: conditions" in prompt
    assert "TABLE: medications" in prompt
    assert "TABLE: encounters" in prompt
    assert "TABLE: observations" in prompt
    assert "STRICT RULES" in prompt
    assert "Do not directly select PII columns" in prompt
    assert "Generate SELECT queries only" in prompt


def test_clean_sql_output():
    """
    Test markdown stripping and whitespace trimming.
    """
    raw_markdown_sql = "```sql\nSELECT COUNT(*) FROM patients;\n```"
    cleaned = clean_sql_output(raw_markdown_sql)
    assert cleaned == "SELECT COUNT(*) FROM patients;"

    raw_generic_fence = "```\nSELECT id FROM conditions;\n```"
    cleaned_generic = clean_sql_output(raw_generic_fence)
    assert cleaned_generic == "SELECT id FROM conditions;"

    raw_plain = "  SELECT hospital_id FROM encounters  "
    cleaned_plain = clean_sql_output(raw_plain)
    assert cleaned_plain == "SELECT hospital_id FROM encounters"


@patch("requests.post")
def test_call_ollama(mock_post):
    """
    Test Ollama API caller with mocked response.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": "SELECT hospital_id, COUNT(*) FROM conditions GROUP BY hospital_id HAVING COUNT(*) >= 5"
    }
    mock_post.return_value = mock_response

    output = call_ollama("Test prompt")
    assert "SELECT hospital_id" in output
    mock_post.assert_called_once()


@patch("pipeline.call_ollama")
def test_generate_sql_mocked(mock_call_ollama):
    """
    Test generate_sql end-to-end with mocked LLM output.
    """
    mock_llm_response = "```sql\nSELECT hospital_id, COUNT(*) AS total FROM patients GROUP BY hospital_id HAVING COUNT(*) >= 5;\n```"
    mock_call_ollama.return_value = mock_llm_response

    question = "How many patients per hospital?"
    result = generate_sql(question, SCHEMA)

    assert isinstance(result, dict)
    assert "sql" in result
    assert "raw_llm_output" in result
    assert result["raw_llm_output"] == mock_llm_response
    assert result["sql"] == "SELECT hospital_id, COUNT(*) AS total FROM patients GROUP BY hospital_id HAVING COUNT(*) >= 5;"
    assert not result["sql"].startswith("```")


if __name__ == "__main__":
    test_build_prompt()
    test_clean_sql_output()
    test_call_ollama()
    test_generate_sql_mocked()

    print("\nAll SQL generation tests passed successfully!")
