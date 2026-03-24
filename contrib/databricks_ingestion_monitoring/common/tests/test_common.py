"""
Tests for pure utility functions in the common module:
parse_comma_separated_list, is_parameter_defined, parse_tag_value_pairs.

Heavy SDK dependencies (databricks.sdk, pyspark) are mocked so that
tests can run without those packages installed.
"""

import os
import sys
from unittest.mock import MagicMock

# Mock heavy dependencies before importing the module under test
sys.modules["databricks"] = MagicMock()
sys.modules["databricks.sdk"] = MagicMock()
sys.modules["databricks.sdk.service"] = MagicMock()
sys.modules["databricks.sdk.service.dashboards"] = MagicMock()
sys.modules["databricks.sdk.service.sql"] = MagicMock()
sys.modules["pyspark"] = MagicMock()
sys.modules["pyspark.sql"] = MagicMock()

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "lib")
)

from databricks_ingestion_monitoring.common import (  # noqa: E402
    is_parameter_defined,
    parse_comma_separated_list,
    parse_tag_value_pairs,
)

# ---------------------------------------------------------------------------
# parse_comma_separated_list
# ---------------------------------------------------------------------------


class TestParseCommaSeparatedList:
    def test_none_returns_empty(self):
        assert parse_comma_separated_list(None) == []

    def test_empty_string_returns_empty(self):
        assert parse_comma_separated_list("") == []

    def test_simple_csv(self):
        assert parse_comma_separated_list("a,b,c") == ["a", "b", "c"]

    def test_strips_whitespace(self):
        assert parse_comma_separated_list(" a , b ") == ["a", "b"]

    def test_consecutive_commas_skip_empty(self):
        assert parse_comma_separated_list(",,") == []

    def test_single_item(self):
        assert parse_comma_separated_list("abc") == ["abc"]

    def test_whitespace_only_returns_empty(self):
        assert parse_comma_separated_list("  ") == []

    def test_mixed_empty_and_nonempty(self):
        assert parse_comma_separated_list("a,,b, ,c") == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# is_parameter_defined
# ---------------------------------------------------------------------------


class TestIsParameterDefined:
    def test_none_is_false(self):
        assert is_parameter_defined(None) is False

    def test_empty_string_is_false(self):
        assert is_parameter_defined("") is False

    def test_whitespace_only_is_false(self):
        assert is_parameter_defined("  ") is False

    def test_non_empty_is_true(self):
        assert is_parameter_defined("x") is True

    def test_string_with_content_and_spaces_is_true(self):
        assert is_parameter_defined("  hello  ") is True


# ---------------------------------------------------------------------------
# parse_tag_value_pairs
# ---------------------------------------------------------------------------


class TestParseTagValuePairs:
    def test_none_returns_empty(self):
        assert parse_tag_value_pairs(None) == []

    def test_empty_string_returns_empty(self):
        assert parse_tag_value_pairs("") == []

    def test_whitespace_only_returns_empty(self):
        assert parse_tag_value_pairs("   ") == []

    def test_single_tag_value(self):
        result = parse_tag_value_pairs("env:prod")
        assert result == [[("env", "prod")]]

    def test_and_logic_comma_separated(self):
        result = parse_tag_value_pairs("env:prod,tier:T0")
        assert result == [[("env", "prod"), ("tier", "T0")]]

    def test_or_logic_semicolon_separated(self):
        result = parse_tag_value_pairs("env:prod;env:staging")
        assert result == [[("env", "prod")], [("env", "staging")]]

    def test_mixed_or_and_logic(self):
        result = parse_tag_value_pairs("tier:T0;team:data,tier:T1")
        assert result == [[("tier", "T0")], [("team", "data"), ("tier", "T1")]]

    def test_tag_without_value(self):
        result = parse_tag_value_pairs("monitoring")
        assert result == [[("monitoring", "")]]

    def test_whitespace_handling(self):
        result = parse_tag_value_pairs(" tier : T0 ; team : data ")
        assert result == [[("tier", "T0")], [("team", "data")]]

    def test_tag_with_empty_value_via_colon(self):
        result = parse_tag_value_pairs("env:")
        assert result == [[("env", "")]]

    def test_multiple_and_groups_via_or(self):
        result = parse_tag_value_pairs("a:1,b:2;c:3,d:4")
        assert result == [[("a", "1"), ("b", "2")], [("c", "3"), ("d", "4")]]
