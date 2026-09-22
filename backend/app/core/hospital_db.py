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

def run_sql_on_hospital(hospital_id: str, sql: str) -> int:
    config = HOSPITAL_DBS[hospital_id]
    conn = psycopg2.connect(**config)
    cur = conn.cursor()
    try:
        clean_sql = adapt_sql_for_single_hospital(sql)
    except Exception as e:
        print(f"[{hospital_id}] SQL ADAPT ERROR: {e}")
        conn.close()
        return 0
    try:
        cur.execute(clean_sql)
        rows = cur.fetchall()
        if not rows:
            return 0
        return int(rows[0][0]) if len(rows[0]) == 1 else len(rows)
    except Exception as e:
        print(f"[{hospital_id}] SQL ERROR: {e}")
        return 0
    finally:
        cur.close()
        conn.close()