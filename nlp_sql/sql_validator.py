# track_b/sql_validator.py

import re
import sqlglot
from sqlglot import exp


FORBIDDEN_STATEMENTS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "GRANT",
    "REVOKE"
}


DEFAULT_LIMIT = 100

PII_NAMES = {
    "name",
    "full_name",
    "first_name",
    "last_name",
    "address",
    "phone",
    "mobile",
    "email",
    "national_id",
    "national_identifier",
    "ssn"
}


def get_schema_columns(schema: dict) -> set:

    columns = set()

    for table_info in schema.values():
        columns.update(
            table_info["columns"].keys()
        )

    return columns


def get_pii_columns(schema: dict) -> set:

    pii_columns = {name.lower() for name in PII_NAMES}

    for table_info in schema.values():

        for column_name, column_info in table_info.get("columns", {}).items():

            if column_info.get("pii", False):
                pii_columns.add(column_name.lower())

    return pii_columns


def validate_sql(sql: str, schema: dict) -> dict:

    errors = []

    if not sql or not sql.strip():
        return {
            "valid": False,
            "errors": ["SQL query is empty"],
            "sql": sql
        }

    # ---------------------------------------------------------
    # 1. Parse SQL using SQLGlot
    # ---------------------------------------------------------

    try:
        tree = sqlglot.parse_one(
            sql,
            read="postgres"
        )

    except Exception as e:

        return {
            "valid": False,
            "errors": [f"Invalid SQL syntax: {str(e)}"],
            "sql": sql
        }

    if tree is None:
        return {
            "valid": False,
            "errors": ["Invalid SQL syntax: unparseable query."],
            "sql": sql
        }

    # ---------------------------------------------------------
    # 2. Only SELECT queries
    # ---------------------------------------------------------

    if not isinstance(tree, (exp.Select, exp.Union)):

        errors.append(
            "Only SELECT queries are permitted."
        )

    # ---------------------------------------------------------
    # 3. Check forbidden keywords
    # ---------------------------------------------------------

    sql_upper = sql.upper()

    for keyword in FORBIDDEN_STATEMENTS:

        pattern = rf"\b{keyword}\b"

        if re.search(pattern, sql_upper):

            errors.append(
                f"Forbidden SQL operation detected: {keyword}"
            )

    # ---------------------------------------------------------
    # 4. Validate tables and columns
    # ---------------------------------------------------------

    valid_tables = {
        table.lower()
        for table in schema.keys()
    }

    valid_columns = get_schema_columns(schema)

    valid_columns = {
        column.lower()
        for column in valid_columns
    }

    defined_aliases = {
        alias.alias.lower()
        for alias in tree.find_all(exp.Alias)
        if alias.alias
    }
    if hasattr(tree, "selects"):
        for select in tree.selects:
            if getattr(select, "alias", None):
                defined_aliases.add(select.alias.lower())

    defined_ctes = {
        cte.alias_or_name.lower()
        for cte in tree.find_all(exp.CTE)
        if cte.alias_or_name
    }

    # Tables
    for table in tree.find_all(exp.Table):

        table_name = table.name.lower()

        if table_name not in valid_tables and table_name not in defined_ctes:

            errors.append(
                f"Unknown table: {table_name}"
            )

    # Columns
    for column in tree.find_all(exp.Column):

        column_name = column.name.lower()

        if column_name == "*":
            continue

        if column_name not in valid_columns and column_name not in defined_aliases:

            errors.append(
                f"Unknown column: {column_name}"
            )

    # ---------------------------------------------------------
    # 5. PII check
    # ---------------------------------------------------------

    pii_columns = get_pii_columns(schema)

    for column in tree.find_all(exp.Column):

        column_name = column.name.lower()

        if column_name in pii_columns:

            errors.append(
                f"Direct PII column selection is not permitted: "
                f"{column_name}"
            )

    # ---------------------------------------------------------
    # 6. GROUP BY minimum group size
    # ---------------------------------------------------------

    has_group_by = tree.args.get("group")

    if has_group_by:

        has_having = tree.args.get("having")

        if not has_having:

            # We do not blindly rewrite arbitrary GROUP BY
            # expressions here. Instead, flag it for the
            # integration/security layer.
            errors.append(
                "GROUP BY query requires a minimum group-size "
                "guardrail."
            )

    # ---------------------------------------------------------
    # 7. LIMIT enforcement
    # ---------------------------------------------------------

    if isinstance(tree, exp.Select):
        limit_expression = tree.args.get("limit")

        if limit_expression:

            try:

                limit_value = int(
                    limit_expression.expression.name
                )

                if limit_value > DEFAULT_LIMIT:

                    tree.set(
                        "limit",
                        exp.Limit(
                            expression=exp.Literal.number(
                                DEFAULT_LIMIT
                            )
                        )
                    )

            except Exception:
                errors.append(
                    "Invalid LIMIT value."
                )

        else:

            # Aggregate-only queries return a small number of rows,
            # but for general SELECT queries we add a safe limit.
            if not tree.find(exp.Avg) and not tree.find(exp.Count) and not tree.find(exp.Sum) and not tree.find(exp.Max) and not tree.find(exp.Min):

                tree = tree.limit(DEFAULT_LIMIT)

    validated_sql = tree.sql(
        dialect="postgres"
    )

    # ---------------------------------------------------------
    # 8. Final result
    # ---------------------------------------------------------

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "sql": validated_sql
    }