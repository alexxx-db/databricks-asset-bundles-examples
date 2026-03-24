"""
Configuration types and utilities for the ingestion monitoring pipeline.
"""

from collections import namedtuple
from typing import Dict


def sanitize_string_for_dlt_name(s: str) -> str:
    res = ""
    for c in s:
        if c == "." or c == "-":
            res += "_"
        elif c != "`":
            res += c
    return res


class Constants:
    """
    Shared names and other constants
    """

    # Shared table names
    created_pipeline_runs = "created_pipeline_runs"
    standard_pipeline_runs = "standard_pipeline_runs"

    # Miscellaneous
    sql_fields_def_extension_point = "-- fields def extension point"
    where_clause_extension_point = "-- where clause extension point"


class Configuration:
    """
    Base monitoring ETL pipeline configuration
    """

    def __init__(self, conf: Dict[str, str]):
        self.monitoring_catalog = self._required_string_param(
            conf, "monitoring_catalog"
        )
        self.monitoring_schema = self._required_string_param(conf, "monitoring_schema")
        self.directly_monitored_pipeline_ids = conf.get(
            "directly_monitored_pipeline_ids", ""
        )
        self.directly_monitored_pipeline_tags = conf.get(
            "directly_monitored_pipeline_tags", ""
        )
        self.imported_event_log_tables = conf.get("imported_event_log_tables", "")

        # Pipeline tags index configuration
        self.pipeline_tags_index_table_name = conf.get(
            "pipeline_tags_index_table_name", "pipeline_tags_index"
        )
        self.pipeline_tags_index_enabled = (
            conf.get("pipeline_tags_index_enabled", "true").lower() == "true"
        )
        self.pipeline_tags_index_max_age_hours = int(
            conf.get("pipeline_tags_index_max_age_hours", "24")
        )
        self.pipeline_tags_index_api_fallback_enabled = (
            conf.get("pipeline_tags_index_api_fallback_enabled", "true").lower()
            == "true"
        )

    @staticmethod
    def _required_string_param(conf: Dict[str, str], param_name: str):
        val = conf.get(param_name)
        if val is None or len(val.strip()) == 0:
            raise ValueError(f"Missing required parameter '{param_name}'")
        return val


# A helper class to capture metadata about monitored pipelines
PipelineInfo = namedtuple(
    "PipelineInfo",
    field_names=[
        "pipeline_id",
        "pipeline_name",
        "pipeline_link",
        "pipeline_type",
        "default_catalog",
        "default_schema",
        "event_log_source",
        "tags_map",
        "tags_array",
    ],
)
