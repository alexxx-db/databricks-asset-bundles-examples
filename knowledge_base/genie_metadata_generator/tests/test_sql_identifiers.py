"""Tests for SQL identifier validation (injection prevention)."""

import pytest

# Run from repo root with: PYTHONPATH=knowledge_base/genie_metadata_generator pytest knowledge_base/genie_metadata_generator/tests/test_sql_identifiers.py -v
from app.utils.sql_identifiers import (
    InvalidIdentifierError,
    quote_spark_identifier,
    validate_identifier,
    validate_qualified_table_name,
)


class TestValidateIdentifier:
    def test_valid_identifiers(self):
        assert validate_identifier("catalog1") == "catalog1"
        assert validate_identifier("schema_name") == "schema_name"
        assert validate_identifier("table") == "table"
        assert validate_identifier("col_1") == "col_1"
        assert validate_identifier("_private") == "_private"
        assert validate_identifier("a") == "a"

    def test_strips_whitespace(self):
        assert validate_identifier("  my_table  ") == "my_table"

    def test_empty_raises(self):
        with pytest.raises(InvalidIdentifierError, match="cannot be empty"):
            validate_identifier("")
        with pytest.raises(InvalidIdentifierError, match="cannot be empty"):
            validate_identifier("   ")

    def test_invalid_characters_raise(self):
        with pytest.raises(InvalidIdentifierError, match="only contain"):
            validate_identifier("table; DROP TABLE users--")
        with pytest.raises(InvalidIdentifierError, match="only contain"):
            validate_identifier("name-with-dash")
        with pytest.raises(InvalidIdentifierError, match="only contain"):
            validate_identifier("space in name")
        with pytest.raises(InvalidIdentifierError, match="only contain"):
            validate_identifier("quoted\"name")

    def test_too_long_raises(self):
        with pytest.raises(InvalidIdentifierError, match="at most 255"):
            validate_identifier("a" * 256)

    def test_not_string_raises(self):
        with pytest.raises(InvalidIdentifierError, match="must be a string"):
            validate_identifier(123)
        with pytest.raises(InvalidIdentifierError, match="must be a string"):
            validate_identifier(None)


class TestValidateQualifiedTableName:
    def test_three_parts(self):
        assert validate_qualified_table_name("cat.schema.table") == ["cat", "schema", "table"]

    def test_two_parts(self):
        assert validate_qualified_table_name("schema.table") == ["schema", "table"]

    def test_one_part(self):
        assert validate_qualified_table_name("table") == ["table"]

    def test_empty_raises(self):
        with pytest.raises(InvalidIdentifierError, match="cannot be empty"):
            validate_qualified_table_name("")
        with pytest.raises(InvalidIdentifierError, match="cannot be empty"):
            validate_qualified_table_name("  ")

    def test_too_many_parts_raises(self):
        with pytest.raises(InvalidIdentifierError, match="1–3 parts"):
            validate_qualified_table_name("a.b.c.d")

    def test_invalid_part_raises(self):
        with pytest.raises(InvalidIdentifierError, match="only contain"):
            validate_qualified_table_name("cat.schema;DROP TABLE x")


class TestQuoteSparkIdentifier:
    def test_quotes_valid_identifier(self):
        assert quote_spark_identifier("my_col") == "`my_col`"

    def test_invalid_raises(self):
        with pytest.raises(InvalidIdentifierError):
            quote_spark_identifier("bad; name")
