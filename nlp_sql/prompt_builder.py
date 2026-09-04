# track_b/prompt_builder.py

def build_prompt(question: str, schema: dict) -> str:
    schema_text = []

    for table_name, table_info in schema.items():
        schema_text.append(
            f"TABLE: {table_name}\n"
            f"DESCRIPTION: {table_info.get('description', '')}"
        )

        for column_name, column_info in table_info["columns"].items():
            pii = column_info.get("pii", False)

            schema_text.append(
                f"  - {column_name} "
                f"({column_info['type']}) "
                f"[PII={pii}]: "
                f"{column_info.get('description', '')}"
            )

        schema_text.append("")

    schema_text = "\n".join(schema_text)

    prompt = f"""
You are a SQL generation assistant for a privacy-preserving
healthcare analytics system.

Generate SQL ONLY using the database schema provided below.

DATABASE SCHEMA
---------------
{schema_text}

STRICT RULES
------------
1. Generate SELECT queries only.
2. Use only tables and columns present in the schema.
3. Do not invent table names or column names.
4. Do not use INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE,
   CREATE, GRANT, or other data-modification operations.
5. Do not directly select PII columns.
6. Use appropriate JOIN conditions.
7. Use aggregation when the question asks for counts,
   averages, totals, comparisons, or trends.
8. For GROUP BY queries, use a minimum group-size condition
   where appropriate.
9. Do not return patient-level identifying information.
10. Return SQL only. Do not provide explanations or markdown.

RESEARCHER QUESTION
-------------------
{question}

SQL:
"""

    return prompt