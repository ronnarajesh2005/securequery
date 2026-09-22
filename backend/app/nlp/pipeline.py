import re

try:
    from app.nlp.prompt_builder import build_prompt
    from app.nlp.ollama_client import call_ollama
except ImportError:
    try:
        from .prompt_builder import build_prompt
        from .ollama_client import call_ollama
    except ImportError:
        from prompt_builder import build_prompt
        from ollama_client import call_ollama


def clean_sql_output(raw_output: str) -> str:
    """
    Removes common Markdown formatting and conversational wrapping from LLM output,
    extracting the pure SQL query block.
    """
    if not raw_output:
        return ""

    match = re.search(r"```(?:sql)?\s*(.*?)\s*```", raw_output, re.DOTALL | re.IGNORECASE)
    if match:
        sql = match.group(1).strip()
    else:
        sql = raw_output.strip()

    if sql.startswith("`") and sql.endswith("`"):
        sql = sql.strip("`").strip()

    return sql


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