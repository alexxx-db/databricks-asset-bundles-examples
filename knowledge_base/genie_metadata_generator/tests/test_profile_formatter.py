"""Tests for app.data.profile_formatter module."""

import importlib.util
import os

import pytest

# Import profile_formatter directly to avoid app.data.__init__.py pulling in
# profiler/information_schema which have heavy Databricks dependencies.
_mod_path = os.path.join(
    os.path.dirname(__file__),
    os.pardir,
    "app",
    "data",
    "profile_formatter.py",
)
_spec = importlib.util.spec_from_file_location("profile_formatter", _mod_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

format_profile_for_llm = _mod.format_profile_for_llm
format_profile_for_display = _mod.format_profile_for_display
get_profile_summary_stats = _mod.get_profile_summary_stats


@pytest.fixture
def full_profile():
    """A representative profile dict covering all column types."""
    return {
        "table": {"full_name": "catalog.schema.my_table"},
        "table_stats": {
            "row_count": 50000,
            "size_readable": "1.2 GB",
            "format": "delta",
            "num_files": 42,
            "last_modified": "2025-06-15",
            "partition_columns": ["region"],
        },
        "column_profiles": {
            "created_at": {
                "type": "timestamp",
                "stats": {
                    "min_date": "2023-01-01",
                    "max_date": "2025-06-15",
                    "range_days": 896,
                    "days_since_last": 0,
                    "null_percentage": 0,
                },
            },
            "updated_at": {
                "type": "date",
                "stats": {
                    "min_date": "2023-01-01",
                    "max_date": "2025-06-14",
                    "range_days": 895,
                    "days_since_last": 1,
                    "null_percentage": 5.0,
                },
            },
            "status": {
                "type": "string",
                "stats": {
                    "distinct_count": 3,
                    "top_values": [
                        {"value": "active", "count": 30000, "percentage": 60.0},
                        {"value": "inactive", "count": 15000, "percentage": 30.0},
                        {"value": "pending", "count": 5000, "percentage": 10.0},
                    ],
                    "null_percentage": 0,
                },
            },
            "region": {
                "type": "varchar",
                "stats": {
                    "distinct_count": 5,
                    "top_values": [
                        {"value": "West", "count": 12000, "percentage": 24.0},
                        {"value": "East", "count": 11000, "percentage": 22.0},
                    ],
                    "null_percentage": 0,
                },
            },
            "revenue": {
                "type": "double",
                "stats": {
                    "min": 0.0,
                    "max": 99999.99,
                    "avg": 1500.50,
                    "distinct_count": 45000,
                    "null_percentage": 2.5,
                },
            },
            "quantity": {
                "type": "int",
                "stats": {
                    "min": 1,
                    "max": 100,
                    "avg": 12.3,
                    "distinct_count": 100,
                    "null_percentage": 0,
                },
            },
            "is_active": {
                "type": "boolean",
                "stats": {
                    "distribution": {
                        "true": {"count": 35000, "percentage": 70.0},
                        "false": {"count": 15000, "percentage": 30.0},
                    },
                    "null_percentage": 0,
                },
            },
            "notes": {
                "type": "string",
                "stats": {
                    "null_percentage": 45.0,
                    "completeness": 55.0,
                },
            },
        },
    }


class TestFormatProfileForLlm:
    """Tests for format_profile_for_llm()."""

    def test_none_profile(self):
        assert format_profile_for_llm(None) == "No profile data available."

    def test_empty_profile(self):
        assert format_profile_for_llm({}) == "No profile data available."

    def test_table_name_in_output(self, full_profile):
        result = format_profile_for_llm(full_profile)
        assert "## Table Profile:" in result
        assert "catalog.schema.my_table" in result

    def test_row_count(self, full_profile):
        result = format_profile_for_llm(full_profile)
        assert "Row Count" in result
        assert "50,000" in result

    def test_table_stats_fields(self, full_profile):
        result = format_profile_for_llm(full_profile)
        assert "1.2 GB" in result
        assert "delta" in result
        assert "42" in result
        assert "2025-06-15" in result
        assert "region" in result

    def test_date_columns_section(self, full_profile):
        result = format_profile_for_llm(full_profile)
        assert "Key Date/Timestamp Columns" in result
        assert "created_at" in result
        assert "updated_at" in result
        assert "896" in result

    def test_date_updated_today(self, full_profile):
        result = format_profile_for_llm(full_profile)
        assert "(updated today)" in result

    def test_date_updated_yesterday(self, full_profile):
        result = format_profile_for_llm(full_profile)
        assert "(last updated yesterday)" in result

    def test_date_null_percentage(self, full_profile):
        result = format_profile_for_llm(full_profile)
        assert "5.0% NULL" in result

    def test_categorical_columns_section(self, full_profile):
        result = format_profile_for_llm(full_profile)
        assert "Important Categorical Columns" in result
        assert "status" in result
        assert "3 distinct values" in result
        assert "active" in result
        assert "60.0%" in result

    def test_numeric_columns_section(self, full_profile):
        result = format_profile_for_llm(full_profile)
        assert "Numeric Columns" in result
        assert "revenue" in result
        assert "Range:" in result
        assert "quantity" in result

    def test_numeric_range_formatting(self, full_profile):
        result = format_profile_for_llm(full_profile)
        # Integer range for quantity (min=1, max=100 are ints)
        assert "Range: 1 to 100" in result
        # Float range for revenue
        assert "Range: 0.00 to 99,999.99" in result

    def test_boolean_columns_section(self, full_profile):
        result = format_profile_for_llm(full_profile)
        assert "Boolean Columns" in result
        assert "is_active" in result
        assert "70.0%" in result
        assert "30.0%" in result

    def test_data_completeness_section(self, full_profile):
        # notes has 45% null (>10%), so it should appear
        result = format_profile_for_llm(full_profile)
        assert "Data Completeness" in result
        assert "notes" in result
        assert "45.0% NULL" in result

    def test_completeness_skips_low_null(self):
        """Columns with <=10% nulls should not appear in Data Completeness."""
        profile = {
            "table": {"full_name": "t"},
            "column_profiles": {
                "col_a": {
                    "type": "int",
                    "stats": {"null_percentage": 5.0},
                },
            },
        }
        result = format_profile_for_llm(profile)
        # The completeness section should either not appear or not contain col_a
        # because 5% < 10% threshold
        lines = result.split("\n")
        completeness_lines = [line for line in lines if "col_a" in line and "complete" in line.lower()]
        assert len(completeness_lines) == 0

    def test_minimal_profile(self):
        profile = {"table": {"full_name": "minimal.table"}}
        result = format_profile_for_llm(profile)
        assert "## Table Profile: minimal.table" in result


class TestGetProfileSummaryStats:
    """Tests for get_profile_summary_stats()."""

    def test_row_count(self, full_profile):
        summary = get_profile_summary_stats(full_profile)
        assert summary["row_count"] == 50000

    def test_total_columns(self, full_profile):
        summary = get_profile_summary_stats(full_profile)
        assert summary["total_columns"] == 8

    def test_date_columns_count(self, full_profile):
        summary = get_profile_summary_stats(full_profile)
        assert summary["date_columns"] == 2  # created_at (timestamp), updated_at (date)

    def test_categorical_columns_count(self, full_profile):
        summary = get_profile_summary_stats(full_profile)
        assert summary["categorical_columns"] == 3  # status (string), region (varchar), notes (string)

    def test_numeric_columns_count(self, full_profile):
        summary = get_profile_summary_stats(full_profile)
        assert summary["numeric_columns"] == 2  # revenue (double), quantity (int)

    def test_empty_profile(self):
        summary = get_profile_summary_stats({})
        assert summary["row_count"] is None
        assert summary["total_columns"] == 0


class TestFormatProfileForDisplay:
    """Tests for format_profile_for_display()."""

    def test_delegates_to_format_for_llm(self, full_profile):
        llm_result = format_profile_for_llm(full_profile)
        display_result = format_profile_for_display(full_profile)
        assert llm_result == display_result

    def test_none_profile(self):
        assert format_profile_for_display(None) == "No profile data available."
