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


# Known condition/drug keyword -> (source table, filter column, LIKE pattern).
# Mirrors the same keyword set already used in prompt_builder.py's few-shot
# examples and ollama_client.py's mock fallback, so behavior stays consistent
# with the rest of the pipeline. Deliberately NOT exhaustive or fuzzy —
# anything outside this list falls through to normal LLM generation rather
# than guessing at a filter term.
_CONDITION_KEYWORDS = {
    "diabet": ("conditions", "condition_desc", "diabetes"),       # matches diabetes/diabetic
    "hypertens": ("conditions", "condition_desc", "hypertension"),
    "blood pressure": ("conditions", "condition_desc", "hypertension"),
    "cardio": ("conditions", "condition_desc", "cardio"),
    "heart": ("conditions", "condition_desc", "cardio"),
}
_DRUG_KEYWORDS = {
    "metformin": ("medications", "drug_name", "metformin"),
}

_AVG_AGE_PATTERN = re.compile(r"\b(average|mean)\b.{0,20}\bage\b", re.IGNORECASE)


def _detect_avg_age_filter(question: str):
    """
    Returns (table, column, like_pattern) if `question` matches an
    "average/mean age of <known condition/drug> patients" pattern, else
    None. Only the small set of known keywords above is recognized;
    anything else returns None and falls through to the LLM.
    """
    if not _AVG_AGE_PATTERN.search(question):
        return None

    q_lower = question.lower()

    for keyword, spec in _CONDITION_KEYWORDS.items():
        if keyword in q_lower:
            return spec
    for keyword, spec in _DRUG_KEYWORDS.items():
        if keyword in q_lower:
            return spec

    return None


def _build_avg_age_sql(table: str, column: str, like_pattern: str) -> str:
    """
    Deterministic, pre-verified SQL for "average age of X patients"
    questions. Bypasses the LLM entirely for this one query shape, since
    qwen2.5-coder:1.5b has produced malformed SQL for it across multiple
    real runs (ambiguous columns, out-of-scope aliases).

    - Never uses AVG() directly: returns SUM(...) AS total_sum and
      COUNT(...) AS total_count, matching what hospital_db.py's
      _is_sum_count_query and dashboard.py's is_average_query branch
      already expect.
    - Deduplicates to one row per patient BEFORE summing age (via the
      DISTINCT subquery), so a patient with multiple matching rows in
      `table` isn't double-counted in the sum.
    - Every column is fully qualified (t1./t2./distinct_patients.) to
      avoid the ambiguous/out-of-scope column errors seen from the LLM's
      attempts at this same pattern.
    """
    return (
        f"SELECT SUM(distinct_patients.age) AS total_sum, "
        f"COUNT(distinct_patients.patient_id) AS total_count "
        f"FROM (SELECT DISTINCT t2.patient_id AS patient_id, "
        f"EXTRACT(YEAR FROM AGE(t2.date_of_birth)) AS age "
        f"FROM {table} AS t1 "
        f"INNER JOIN patients AS t2 ON t1.patient_id = t2.patient_id "
        f"WHERE LOWER(t1.{column}) LIKE '%{like_pattern}%') AS distinct_patients;"
    )


def generate_sql(question: str, schema: dict) -> dict:

    avg_age_filter = _detect_avg_age_filter(question)
    if avg_age_filter:
        table, column, like_pattern = avg_age_filter
        sql = _build_avg_age_sql(table, column, like_pattern)
        return {
            "sql": sql,
            "raw_llm_output": None,
            "source": "deterministic_template",
        }

    prompt = build_prompt(
        question=question,
        schema=schema
    )

    raw_output = call_ollama(prompt)

    sql = clean_sql_output(raw_output)

    return {
        "sql": sql,
        "raw_llm_output": raw_output,
        "source": "llm",
    }