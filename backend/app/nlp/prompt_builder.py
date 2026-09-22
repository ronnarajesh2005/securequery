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

    examples = """
EXAMPLES
--------
Q: How many patients have diabetes?
SQL: SELECT COUNT(DISTINCT patient_id) AS patient_count FROM conditions WHERE LOWER(condition_desc) LIKE '%diabetes%';

Q: How many patients have hypertension?
SQL: SELECT COUNT(DISTINCT patient_id) AS patient_count FROM conditions WHERE LOWER(condition_desc) LIKE '%hypertension%';

Q: How many patients are taking metformin?
SQL: SELECT COUNT(DISTINCT patient_id) AS patient_count FROM medications WHERE LOWER(drug_name) LIKE '%metformin%';

Q: How many patients have asthma?
SQL: SELECT COUNT(DISTINCT patient_id) AS patient_count FROM conditions WHERE LOWER(condition_desc) LIKE '%asthma%';

Q: Average age of diabetic patients?
SQL: SELECT SUM(patient_age) AS total_sum, COUNT(*) AS total_count FROM (SELECT DISTINCT T2.patient_id, EXTRACT(YEAR FROM AGE(T2.date_of_birth)) AS patient_age FROM conditions AS T1 INNER JOIN patients AS T2 ON T1.patient_id = T2.patient_id WHERE LOWER(T1.condition_desc) LIKE '%diabetes%') AS distinct_patients;

Q: Average age of hypertension patients?
SQL: SELECT SUM(patient_age) AS total_sum, COUNT(*) AS total_count FROM (SELECT DISTINCT T2.patient_id, EXTRACT(YEAR FROM AGE(T2.date_of_birth)) AS patient_age FROM conditions AS T1 INNER JOIN patients AS T2 ON T1.patient_id = T2.patient_id WHERE LOWER(T1.condition_desc) LIKE '%hypertension%') AS distinct_patients;

RULE FOR NEW CONDITIONS OR DRUGS NOT SHOWN ABOVE: follow the
same pattern — filter the relevant table's description/name
column using LOWER(column) LIKE '%keyword%', where keyword is
the condition or drug name mentioned in the question.

RULE FOR "AVERAGE" OR "MEAN" QUESTIONS (ANY METRIC, NOT JUST AGE):
NEVER use the AVG() SQL function, for any column, under any
circumstances. Instead ALWAYS return SUM(...) AS total_sum and
COUNT(...) AS total_count as two separate columns. The true
average will be computed later by dividing total_sum by
total_count. A query using AVG() directly will be REJECTED —
always use the SUM + COUNT pattern shown in the examples above.

CRITICAL — AVOID JOIN DUPLICATION: a patient can have MULTIPLE
rows in the conditions (or medications) table for the same
condition/drug (e.g. one row per clinical visit/encounter). A
plain JOIN between conditions and patients therefore produces
ONE ROW PER MATCHING CONDITION RECORD, not one row per patient.
Summing a per-patient value (like age) directly over that joined
result will silently double- or triple-count patients with
repeat entries, inflating the sum while leaving COUNT(DISTINCT)
correct — producing a mathematically wrong average.
To prevent this, ALWAYS wrap the join in a subquery that
SELECTs DISTINCT patient_id (plus the per-patient metric, e.g.
age) FIRST, and only SUM/COUNT over that deduplicated result —
exactly as shown in the "Average age of..." examples above. This
applies to any AVERAGE/MEAN question involving a join, not just
age.
"""

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
11. When the question asks about a specific medical condition
    or drug not listed in the examples below, filter using the
    same LIKE pattern shown in the examples — do not fall back
    to an unfiltered COUNT unless the question truly has no
    condition/drug/filter mentioned at all.
12. NEVER use AVG(). See the AVERAGE/MEAN rule below for the
    required SUM + COUNT pattern instead.
13. For AVERAGE/MEAN questions involving a JOIN, always
    deduplicate to one row per patient BEFORE summing — see the
    JOIN DUPLICATION rule below.
{examples}
RESEARCHER QUESTION
-------------------
{question}

SQL:
"""

    return prompt