# track_b/pipeline.py

try:
    from .prompt_builder import build_prompt
    from .ollama_client import call_ollama
except ImportError:
    from prompt_builder import build_prompt
    from ollama_client import call_ollama


def clean_sql_output(raw_output: str) -> str:
    """
    Removes common Markdown formatting from LLM output.
    """

    sql = raw_output.strip()

    if sql.startswith("```sql"):
        sql = sql[6:]

    elif sql.startswith("```"):
        sql = sql[3:]

    if sql.endswith("```"):
        sql = sql[:-3]

    return sql.strip()


def generate_sql(question: str, schema: dict) -> dict:

    prompt = build_prompt(
        question=question,
        schema=schema
    )

    raw_output = call_ollama(prompt)

    sql = clean_sql_output(raw_output)

    return {
        "sql": sql,
        "raw_llm_output": raw_output
    }