"""Tests for COMMENT ON TABLE/COLUMN SQL generation (validation and escaping)."""

import pytest
from app.utils.comment_sql import escape_sql_string, generate_comment_sql
from app.utils.sql_identifiers import InvalidIdentifierError


class TestEscapeSqlString:
    def test_no_quotes_unchanged(self):
        assert escape_sql_string("hello") == "hello"
        assert escape_sql_string("col_desc") == "col_desc"

    def test_single_quote_escaped(self):
        assert escape_sql_string("it's") == "it''s"
        assert escape_sql_string("''") == "''''"


class TestGenerateCommentSql:
    def test_table_comment_valid(self):
        sql = generate_comment_sql("cat.schema.table", None, "Table description")
        assert sql == "COMMENT ON TABLE cat.schema.table IS 'Table description';"

    def test_column_comment_valid(self):
        sql = generate_comment_sql("cat.schema.table", "col_name", "Column description")
        assert sql == "COMMENT ON COLUMN cat.schema.table.col_name IS 'Column description';"

    def test_description_escaping(self):
        sql = generate_comment_sql("c.s.t", None, "It's a test")
        assert sql == "COMMENT ON TABLE c.s.t IS 'It''s a test';"

    def test_invalid_table_name_raises(self):
        with pytest.raises(InvalidIdentifierError):
            generate_comment_sql("cat.schema.table; DROP TABLE t--", None, "x")
        with pytest.raises(InvalidIdentifierError):
            generate_comment_sql("", None, "x")

    def test_invalid_column_name_raises(self):
        with pytest.raises(InvalidIdentifierError):
            generate_comment_sql("cat.schema.table", "col; DROP TABLE t--", "x")
        with pytest.raises(InvalidIdentifierError):
            generate_comment_sql("cat.schema.table", "col-name", "x")
