# track_b/demo_pipeline.py
"""
SecureQuery - Track B End-to-End Demonstration Script.

Runs sample clinical research questions through:
1. Schema-aware Prompt Builder
2. Ollama / Qwen2.5-Coder (with offline fallback if Ollama is not running)
3. AST Validation & Privacy Guardrails
4. Privacy Feature Extraction (for Track C)
"""

import os
import sys
import json
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from track_b import generate_sql, validate_sql, extract_features, check_ollama_status
from track_b.schemas.mock_schema import SCHEMA


def mock_database_counter(sql_query: str) -> int:
    """
    Simulates the lightweight pre-flight COUNT callback from integration/Track C.
    """
    if "H001" in sql_query:
        return 18
    elif "metformin" in sql_query.lower():
        return 45
    return 120


def run_pipeline_demo():
    print("=" * 70)
    print(" SecureQuery Track B: Privacy-Preserving NLP-to-SQL Pipeline Demo")
    print("=" * 70)

    # 1. Check Ollama daemon status
    ollama_info = check_ollama_status()
    print("\n[1] Ollama Status Check:")
    if ollama_info["running"]:
        print(f"  Ollama Server: RUNNING at {os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}")
        if ollama_info["model_available"]:
            print(f"  Target Model (qwen2.5-coder): AVAILABLE")
        else:
            print(f"  Target Model (qwen2.5-coder): NOT FOUND in {ollama_info['installed_models']}")
            print("  Falling back to simulation mode for this demo...")
            os.environ["MOCK_OLLAMA"] = "true"
    else:
        print("  Ollama Server: NOT RUNNING (or not yet installed)")
        print("  Running demo in simulation mode (MOCK_OLLAMA=true)...")
        print("  (To run live: install Ollama, run `ollama pull qwen2.5-coder` and `ollama serve`)")
        os.environ["MOCK_OLLAMA"] = "true"

    sample_questions = [
        "How many diabetes patients per hospital in 2024?",
        "What is the patient count for patients on metformin across hospitals?",
        "Count of diabetes patients in hospital H001"
    ]

    for i, question in enumerate(sample_questions, 1):
        print("\n" + "-" * 70)
        print(f" Query {i}: \"{question}\"")
        print("-" * 70)

        # Step A: Generate SQL
        gen_result = generate_sql(question, SCHEMA)
        sql = gen_result["sql"]
        print(f"\n[Generated SQL]:\n  {sql}")

        # Step B: Validate SQL & Guardrails
        val_result = validate_sql(sql, SCHEMA)
        print(f"\n[Validation Result]:")
        print(f"  Valid: {val_result['valid']}")
        print(f"  Errors: {val_result['errors']}")
        print(f"  Validated/Rewritten SQL: {val_result['sql']}")

        # Step C: Extract Features (if valid)
        if val_result["valid"]:
            features = extract_features(
                val_result["sql"],
                SCHEMA,
                count_callback=mock_database_counter
            )
            print(f"\n[Extracted Features for Track C Risk Classifier]:")
            for k, v in features.items():
                print(f"  - {k}: {v}")

    # Step D: Test an unsafe query violating privacy guardrails
    print("\n" + "-" * 70)
    print(" Testing Privacy Guardrail: Unsafe Direct PII Query")
    print("-" * 70)
    unsafe_sql = "SELECT name, birth_date, address FROM patients"
    print(f"\n[Attempted SQL]:\n  {unsafe_sql}")
    unsafe_val = validate_sql(unsafe_sql, SCHEMA)
    print(f"\n[Validation Result]:")
    print(f"  Valid: {unsafe_val['valid']} (Strictly Rejected!)")
    print(f"  Errors Triggered:")
    for err in unsafe_val["errors"]:
        print(f"    * {err}")

    print("\n" + "=" * 70)
    print(" Demo completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    run_pipeline_demo()
