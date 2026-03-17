"""
SQL identifier validation for safe interpolation into SQL statements.

Use these helpers whenever catalog, schema, table, or column names
from user or UI input are used in SQL to prevent identifier/SQL injection.
"""

import re
from typing import List

# Unity Catalog / Spark unquoted identifiers: alphanumeric and underscore.
# Reject empty, quotes, semicolons, and other metacharacters.
_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")
_MAX_IDENTIFIER_LENGTH = 255


class InvalidIdentifierError(ValueError):
    """Raised when an identifier fails validation."""

    pass


def validate_identifier(name: str, kind: str = "identifier") -> str:
    """
    Validate a single SQL identifier (catalog, schema, table, column).

    Args:
        name: The identifier string to validate.
        kind: Label for error messages (e.g. "catalog", "column").

    Returns:
        The same string if valid.

    Raises:
        InvalidIdentifierError: If the identifier is empty, too long, or
            contains disallowed characters.
    """
    if not isinstance(name, str):
        raise InvalidIdentifierError(f"{kind} must be a string, got {type(name).__name__}")
    s = name.strip()
    if not s:
        raise InvalidIdentifierError(f"{kind} cannot be empty")
    if len(s) > _MAX_IDENTIFIER_LENGTH:
        raise InvalidIdentifierError(
            f"{kind} must be at most {_MAX_IDENTIFIER_LENGTH} characters, got {len(s)}"
        )
    if not _IDENTIFIER_PATTERN.match(s):
        raise InvalidIdentifierError(
            f"{kind} may only contain letters, digits, and underscores, got: {s!r}"
        )
    return s


def validate_qualified_table_name(qualified_name: str) -> List[str]:
    """
    Validate a qualified table name (e.g. catalog.schema.table) and return parts.

    Args:
        qualified_name: A dot-separated name with 1–3 parts.

    Returns:
        List of validated identifier parts (e.g. [catalog, schema, table]).

    Raises:
        InvalidIdentifierError: If any part is invalid or the format is wrong.
    """
    if not isinstance(qualified_name, str) or not qualified_name.strip():
        raise InvalidIdentifierError("qualified table name cannot be empty")
    parts = [p.strip() for p in qualified_name.split(".") if p.strip()]
    if not parts or len(parts) > 3:
        raise InvalidIdentifierError(
            "qualified table name must be 1–3 parts (catalog.schema.table), "
            f"got {len(parts)} parts"
        )
    validated = []
    for i, part in enumerate(parts):
        kind = ["catalog", "schema", "table"][i] if len(parts) == 3 else "identifier"
        if len(parts) == 2 and i == 0:
            kind = "catalog_or_schema"
        validated.append(validate_identifier(part, kind=kind))
    return validated


def quote_spark_identifier(name: str) -> str:
    """
    Return a Spark/Databricks backtick-quoted identifier after validation.

    Use for building full_name and column references in SQL.
    """
    validated = validate_identifier(name, "identifier")
    return f"`{validated}`"
