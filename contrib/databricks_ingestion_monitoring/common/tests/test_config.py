"""
Tests for the config module: sanitize_string_for_dlt_name, Configuration, and PipelineInfo.
"""

import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "lib")
)

import pytest
from databricks_ingestion_monitoring.config import (
    Configuration,
    PipelineInfo,
    sanitize_string_for_dlt_name,
)

# ---------------------------------------------------------------------------
# sanitize_string_for_dlt_name
# ---------------------------------------------------------------------------


class TestSanitizeStringForDltName:
    def test_dots_become_underscores(self):
        assert sanitize_string_for_dlt_name("a.b.c") == "a_b_c"

    def test_dashes_become_underscores(self):
        assert sanitize_string_for_dlt_name("a-b-c") == "a_b_c"

    def test_backticks_are_removed(self):
        assert sanitize_string_for_dlt_name("`my`table`") == "mytable"

    def test_normal_alphanumeric_passes_through(self):
        assert sanitize_string_for_dlt_name("abc123_XYZ") == "abc123_XYZ"

    def test_empty_string_returns_empty(self):
        assert sanitize_string_for_dlt_name("") == ""

    def test_mixed_special_characters(self):
        assert sanitize_string_for_dlt_name("`a.b-c`") == "a_b_c"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class TestConfiguration:
    def test_valid_config_with_required_params(self):
        conf = {
            "monitoring_catalog": "my_catalog",
            "monitoring_schema": "my_schema",
        }
        cfg = Configuration(conf)
        assert cfg.monitoring_catalog == "my_catalog"
        assert cfg.monitoring_schema == "my_schema"

    def test_missing_monitoring_catalog_raises(self):
        conf = {"monitoring_schema": "my_schema"}
        with pytest.raises(ValueError, match="monitoring_catalog"):
            Configuration(conf)

    def test_missing_monitoring_schema_raises(self):
        conf = {"monitoring_catalog": "my_catalog"}
        with pytest.raises(ValueError, match="monitoring_schema"):
            Configuration(conf)

    def test_empty_string_for_required_param_raises(self):
        conf = {
            "monitoring_catalog": "",
            "monitoring_schema": "my_schema",
        }
        with pytest.raises(ValueError, match="monitoring_catalog"):
            Configuration(conf)

    def test_whitespace_only_for_required_param_raises(self):
        conf = {
            "monitoring_catalog": "   ",
            "monitoring_schema": "my_schema",
        }
        with pytest.raises(ValueError, match="monitoring_catalog"):
            Configuration(conf)

    def test_optional_defaults_pipeline_tags_index_enabled(self):
        conf = {
            "monitoring_catalog": "cat",
            "monitoring_schema": "sch",
        }
        cfg = Configuration(conf)
        assert cfg.pipeline_tags_index_enabled is True

    def test_optional_defaults_pipeline_tags_index_max_age_hours(self):
        conf = {
            "monitoring_catalog": "cat",
            "monitoring_schema": "sch",
        }
        cfg = Configuration(conf)
        assert cfg.pipeline_tags_index_max_age_hours == 24

    def test_optional_defaults_pipeline_tags_index_table_name(self):
        conf = {
            "monitoring_catalog": "cat",
            "monitoring_schema": "sch",
        }
        cfg = Configuration(conf)
        assert cfg.pipeline_tags_index_table_name == "pipeline_tags_index"

    def test_optional_defaults_api_fallback_enabled(self):
        conf = {
            "monitoring_catalog": "cat",
            "monitoring_schema": "sch",
        }
        cfg = Configuration(conf)
        assert cfg.pipeline_tags_index_api_fallback_enabled is True

    def test_optional_defaults_directly_monitored_fields(self):
        conf = {
            "monitoring_catalog": "cat",
            "monitoring_schema": "sch",
        }
        cfg = Configuration(conf)
        assert cfg.directly_monitored_pipeline_ids == ""
        assert cfg.directly_monitored_pipeline_tags == ""
        assert cfg.imported_event_log_tables == ""

    def test_boolean_parsing_false(self):
        conf = {
            "monitoring_catalog": "cat",
            "monitoring_schema": "sch",
            "pipeline_tags_index_enabled": "false",
        }
        cfg = Configuration(conf)
        assert cfg.pipeline_tags_index_enabled is False

    def test_boolean_parsing_true_explicit(self):
        conf = {
            "monitoring_catalog": "cat",
            "monitoring_schema": "sch",
            "pipeline_tags_index_enabled": "true",
        }
        cfg = Configuration(conf)
        assert cfg.pipeline_tags_index_enabled is True

    def test_boolean_parsing_case_insensitive(self):
        conf = {
            "monitoring_catalog": "cat",
            "monitoring_schema": "sch",
            "pipeline_tags_index_enabled": "False",
            "pipeline_tags_index_api_fallback_enabled": "TRUE",
        }
        cfg = Configuration(conf)
        assert cfg.pipeline_tags_index_enabled is False
        assert cfg.pipeline_tags_index_api_fallback_enabled is True

    def test_custom_max_age_hours(self):
        conf = {
            "monitoring_catalog": "cat",
            "monitoring_schema": "sch",
            "pipeline_tags_index_max_age_hours": "48",
        }
        cfg = Configuration(conf)
        assert cfg.pipeline_tags_index_max_age_hours == 48


# ---------------------------------------------------------------------------
# PipelineInfo
# ---------------------------------------------------------------------------


class TestPipelineInfo:
    def test_is_namedtuple_with_expected_fields(self):
        expected_fields = [
            "pipeline_id",
            "pipeline_name",
            "pipeline_link",
            "pipeline_type",
            "default_catalog",
            "default_schema",
            "event_log_source",
            "tags_map",
            "tags_array",
        ]
        assert list(PipelineInfo._fields) == expected_fields

    def test_can_be_created_with_all_positional_args(self):
        pi = PipelineInfo(
            "id1",
            "name1",
            "link1",
            "type1",
            "catalog1",
            "schema1",
            "event_log1",
            {"env": "prod"},
            [("env", "prod")],
        )
        assert pi.pipeline_id == "id1"
        assert pi.pipeline_name == "name1"
        assert pi.pipeline_link == "link1"
        assert pi.pipeline_type == "type1"
        assert pi.default_catalog == "catalog1"
        assert pi.default_schema == "schema1"
        assert pi.event_log_source == "event_log1"
        assert pi.tags_map == {"env": "prod"}
        assert pi.tags_array == [("env", "prod")]
