import sqlglot
from sqlglot import exp

FORBIDDEN_STATEMENTS = (
    exp.Insert, exp.Update, exp.Delete, exp.Drop,
    exp.Alter, exp.Create, exp.TruncateTable,
)

# Columns that should never be directly selected (raw PII)
PII_COLUMNS = {"first_name", "last_name", "email", "zip_code"}

MIN_GROUP_SIZE = 5


def validate_sql(sql: str, schema: dict) -> dict:
    """
    Returns: {"valid": bool, "errors": list[str], "sql": str}
    (sql may be rewritten, e.g. LIMIT inserted)
    """
    errors = []

    try:
        tree = sqlglot.parse_one(sql, read="postgres")
    except Exception as e:
        return {"valid": False, "errors": [f"SQL parse error: {e}"], "sql": sql}

    # Rule 1: must be a SELECT
    if not isinstance(tree, exp.Select):
        errors.append("Only SELECT statements are permitted.")

    # Rule 2: block any modification statements
    for forbidden_type in FORBIDDEN_STATEMENTS:
        if tree.find(forbidden_type):
            errors.append(f"Forbidden statement type detected: {forbidden_type.__name__}")

    # Rule 3: block direct selection of PII columns
    selected_columns = {col.name.lower() for col in tree.find_all(exp.Column)}
    pii_hit = selected_columns & PII_COLUMNS
    if pii_hit:
        errors.append(f"Direct selection of PII column(s) not allowed: {sorted(pii_hit)}")

    # Rule 4: validate tables/columns exist in schema (only if schema given)
    if schema:
        valid_tables = set(schema.keys())
        used_tables = {t.name.lower() for t in tree.find_all(exp.Table)}
        unknown_tables = used_tables - valid_tables
        if unknown_tables:
            errors.append(f"Unknown table(s) referenced: {sorted(unknown_tables)}")

    if errors:
        return {"valid": False, "errors": errors, "sql": sql}

    return {"valid": True, "errors": [], "sql": tree.sql(dialect="postgres")}