"""Generate COMMENT ON TABLE/COLUMN SQL with validation and escaping."""

from typing import Optional

from app.utils.sql_identifiers import (
    validate_identifier,
    validate_qualified_table_name,
)


def escape_sql_string(text: str) -> str:
    """Escape single quotes for SQL."""
    return text.replace("'", "''")


def generate_comment_sql(
    table_name: str, column_name: Optional[str], description: str
) -> str:
    """
    Generate COMMENT ON TABLE/COLUMN SQL statement.

    Validates table_name and column_name to prevent identifier/SQL injection.

    Args:
        table_name: Fully qualified table name (catalog.schema.table)
        column_name: Column name (None for table comments)
        description: Description text

    Returns:
        SQL statement as string

    Raises:
        InvalidIdentifierError: If table_name or column_name fail validation.
    """
    parts = validate_qualified_table_name(table_name)
    table_ref = ".".join(parts)
    escaped_desc = escape_sql_string(description)

    if column_name:
        col = validate_identifier(column_name, "column")
        return f"COMMENT ON COLUMN {table_ref}.{col} IS '{escaped_desc}';"
    return f"COMMENT ON TABLE {table_ref} IS '{escaped_desc}';"
