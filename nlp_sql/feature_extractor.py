# track_b/feature_extractor.py

import sqlglot
from sqlglot import exp
from typing import Callable, Optional, Dict, Any, Set


SENSITIVE_COLUMNS = {
    "description",
    "code",
    "value",
    "encounter_type",
    "diagnosis",
    "condition",
    "medication"
}


def _extract_filter_count(tree: exp.Expression) -> int:
    """
    Counts the number of filtering predicates in the WHERE clause.
    """
    where = tree.find(exp.Where)
    if not where:
        return 0

    # Find all comparison/predicate expressions
    predicates = list(where.find_all(exp.Predicate))
    if predicates:
        return len(predicates)

    # Fallback if WHERE exists without explicit standard Predicate node
    return 1


def _is_single_hospital(tree: exp.Expression) -> bool:
    """
    Determines whether the query specifically restricts to a single hospital.
    """
    where = tree.find(exp.Where)
    if not where:
        return False

    for eq in where.find_all(exp.EQ):
        columns = [col.name.lower() for col in eq.find_all(exp.Column)]
        if "hospital_id" in columns:
            return True

    for in_expr in where.find_all(exp.In):
        columns = [col.name.lower() for col in in_expr.find_all(exp.Column)]
        if "hospital_id" in columns:
            expressions = in_expr.expressions
            if expressions and len(expressions) == 1:
                return True

    return False


def _extract_distinct_sensitive_values(tree: exp.Expression, schema: dict) -> int:
    """
    Counts distinct sensitive attribute values or sensitive columns referenced.
    """
    sensitive_values: Set[str] = set()
    sensitive_cols_found: Set[str] = set()

    # Identify any columns flagged as sensitive in schema or default list
    schema_sensitive_cols = set(SENSITIVE_COLUMNS)
    for table_name, table_info in schema.items():
        for col_name, col_info in table_info.get("columns", {}).items():
            if col_info.get("sensitive", False) or col_info.get("pii", False):
                schema_sensitive_cols.add(col_name.lower())

    where = tree.find(exp.Where)
    if where:
        for binary in where.find_all(exp.Binary):
            cols = [c.name.lower() for c in binary.find_all(exp.Column)]
            literals = [l.name for l in binary.find_all(exp.Literal)]
            for col in cols:
                if col in schema_sensitive_cols:
                    sensitive_cols_found.add(col)
                    for lit in literals:
                        sensitive_values.add(str(lit))

        for in_expr in where.find_all(exp.In):
            cols = [c.name.lower() for c in in_expr.find_all(exp.Column)]
            for col in cols:
                if col in schema_sensitive_cols:
                    sensitive_cols_found.add(col)
                    for expr in in_expr.expressions:
                        if isinstance(expr, exp.Literal):
                            sensitive_values.add(str(expr.name))

    # Also check sensitive columns in SELECT or GROUP BY if no literal filters
    for col in tree.find_all(exp.Column):
        col_name = col.name.lower()
        if col_name in schema_sensitive_cols:
            sensitive_cols_found.add(col_name)

    if sensitive_values:
        return len(sensitive_values)
    return len(sensitive_cols_found)


def _compute_attribute_rarity(
    num_filters: int,
    distinct_sensitive_values: int,
    single_hospital: bool
) -> float:
    """
    Calculates normalized rarity score between 0.0 and 1.0.
    Higher values indicate narrower, more identifying queries.
    """
    if num_filters == 0 and distinct_sensitive_values == 0 and not single_hospital:
        return 0.0

    weight = (
        0.3 * num_filters
        + 0.2 * distinct_sensitive_values
        + (0.25 if single_hospital else 0.0)
    )
    rarity = 1.0 - (1.0 / (1.0 + weight))
    return round(min(max(rarity, 0.0), 1.0), 4)


def extract_features(
    sql: str,
    schema: dict,
    count_callback: Optional[Callable[[str], Any]] = None
) -> Dict[str, Any]:
    """
    Extracts privacy risk features from a SQL query.

    Args:
        sql: The SQL query string to analyze.
        schema: The database schema dictionary.
        count_callback: Optional callable hook taking SQL and returning COUNT.

    Returns:
        Dictionary containing:
            - num_filters (int)
            - predicted_result_count (int | None)
            - distinct_sensitive_values (int)
            - single_hospital (bool)
            - attribute_rarity (float)
    """
    try:
        tree = sqlglot.parse_one(sql, read="postgres")
    except Exception:
        tree = None

    if tree is None:
        return {
            "num_filters": 0,
            "predicted_result_count": None,
            "distinct_sensitive_values": 0,
            "single_hospital": False,
            "attribute_rarity": 0.0
        }

    num_filters = _extract_filter_count(tree)
    single_hospital = _is_single_hospital(tree)
    distinct_sensitive_values = _extract_distinct_sensitive_values(tree, schema)
    attribute_rarity = _compute_attribute_rarity(
        num_filters=num_filters,
        distinct_sensitive_values=distinct_sensitive_values,
        single_hospital=single_hospital
    )

    predicted_result_count = None
    if callable(count_callback):
        try:
            result = count_callback(sql)
            if result is not None:
                predicted_result_count = int(result)
        except Exception:
            predicted_result_count = None

    return {
        "num_filters": num_filters,
        "predicted_result_count": predicted_result_count,
        "distinct_sensitive_values": distinct_sensitive_values,
        "single_hospital": single_hospital,
        "attribute_rarity": attribute_rarity
    }
