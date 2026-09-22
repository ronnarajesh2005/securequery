import psycopg2
import sqlglot
from sqlglot import exp

HOSPITAL_DBS = {
    "hospital_a": {"host": "localhost", "port": 5433, "database": "hospital_a", "user": "hospital_a_admin", "password": "HospitalA_2026!"},
    "hospital_b": {"host": "localhost", "port": 5434, "database": "hospital_b", "user": "hospital_b_admin", "password": "HospitalB_2026!"},
    "hospital_c": {"host": "localhost", "port": 5435, "database": "hospital_c", "user": "hospital_c_admin", "password": "HospitalC_2026!"},
}

def adapt_sql_for_single_hospital(sql: str) -> str:
    tree = sqlglot.parse_one(sql, read="postgres")
    tree.set("group", None)
    tree.set("having", None)
    new_expressions = [
        e for e in tree.expressions
        if not (isinstance(e, exp.Column) and e.name.lower() == "hospital_id")
    ]
    tree.set("expressions", new_expressions)
    return tree.sql(dialect="postgres")


def _is_sum_count_query(sql: str) -> bool:
    """
    Detects the SUM(...)/COUNT(...) two-column aggregate pattern used
    for average-style questions (see prompt_builder.py). Looked for by
    output alias, not just function name, so this stays robust even if
    column order changes.
    """
    try:
        tree = sqlglot.parse_one(sql, read="postgres")
    except Exception:
        return False
    aliases = {e.alias.lower() for e in tree.expressions if hasattr(e, "alias") and e.alias}
    return "total_sum" in aliases and "total_count" in aliases


def run_sql_on_hospital(hospital_id: str, sql: str):
    """
    Returns:
      - int, for a single-column COUNT-style query (unchanged behavior)
      - dict {"sum": float, "count": int}, for a SUM(...) AS total_sum,
        COUNT(...) AS total_count two-column query (average-style)
    Returns 0 (or a zeroed dict, matching the query shape) on any error,
    so a failing hospital never silently corrupts the aggregate for the
    other hospitals.
    """
    config = HOSPITAL_DBS[hospital_id]
    conn = psycopg2.connect(**config)
    cur = conn.cursor()

    sum_count_query = _is_sum_count_query(sql)

    try:
        clean_sql = adapt_sql_for_single_hospital(sql)
    except Exception as e:
        print(f"[{hospital_id}] SQL ADAPT ERROR: {e}")
        conn.close()
        return {"sum": 0, "count": 0} if sum_count_query else 0

    try:
        cur.execute(clean_sql)
        rows = cur.fetchall()

        if not rows:
            return {"sum": 0, "count": 0} if sum_count_query else 0

        if sum_count_query:
            total_sum = rows[0][0] if rows[0][0] is not None else 0
            total_count = rows[0][1] if rows[0][1] is not None else 0
            return {"sum": float(total_sum), "count": int(total_count)}

        # Original COUNT-style single-scalar behavior, unchanged
        return int(rows[0][0]) if len(rows[0]) == 1 else len(rows)

    except Exception as e:
        print(f"[{hospital_id}] SQL ERROR: {e}")
        return {"sum": 0, "count": 0} if sum_count_query else 0
    finally:
        cur.close()
        conn.close()