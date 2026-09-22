import sys
sys.path.insert(0, r"D:\securequery\backend")

from app.nlp.prompt_builder import build_prompt
from app.nlp.ollama_client import call_ollama
from app.nlp.pipeline import clean_sql_output
from app.schemas.mock_schema import SCHEMA

question = "How many patients are on aspirin?"
prompt = build_prompt(question, SCHEMA)

print("=== PROMPT SENT ===")
print(prompt)
print("\n=== RAW OLLAMA OUTPUT ===")
raw = call_ollama(prompt)
print(raw)
print("\n=== CLEANED SQL ===")
print(clean_sql_output(raw))