"""
Configuration module for Genify App.
Loads settings from app.yaml with environment variable overrides.
"""

import os
from pathlib import Path

import yaml


class AppConfig:
    """Load and manage app configuration from app.yaml."""

    def __init__(self):
        config_path = Path(__file__).parent / "app.yaml"
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

    @property
    def llm_endpoint_name(self):
        """LLM endpoint name from config or env."""
        return os.getenv("LLM_ENDPOINT_NAME") or \
               self.config.get("config", {}).get("llm", {}).get("endpoint_name")

    @property
    def llm_max_tokens(self):
        """
        Maximum output tokens per LLM request.

        Default: 2048 (safe for GPT-5.2 OTPM limit of 5,000)
        Note: This is per-request limit. Multiple requests contribute to OTPM rate limit.
        See: https://docs.databricks.com/gcp/en/machine-learning/foundation-model-apis/limits
        """
        return self.config.get("config", {}).get("llm", {}).get("max_tokens", 2048)

    @property
    def llm_temperature(self):
        return self.config.get("config", {}).get("llm", {}).get("temperature", 0.7)

    @property
    def summarizer_endpoint_name(self):
        """
        Summarizer endpoint name from env (resource key) or config.

        Priority:
        1. SUMMARIZER_ENDPOINT_NAME environment variable (from serving-endpoint-2 resource)
        2. config.llm.summarizer_endpoint_name from app.yaml
        3. Falls back to main LLM endpoint
        """
        return os.getenv("SUMMARIZER_ENDPOINT_NAME") or \
               self.config.get("config", {}).get("llm", {}).get("summarizer_endpoint_name") or \
               self.llm_endpoint_name  # Fallback to main endpoint

    @property
    def summarizer_max_tokens(self):
        """Max tokens for summarization output (Gemini Flash supports large outputs)."""
        return self.config.get("config", {}).get("llm", {}).get("summarizer_max_tokens", 8192)

    @property
    def summarizer_temperature(self):
        """Temperature for summarization (lower for focused, deterministic summaries)."""
        return self.config.get("config", {}).get("llm", {}).get("summarizer_temperature", 0.3)

    @property
    def sql_warehouse_id(self):
        """
        SQL Warehouse ID from env or config.

        Priority:
        1. DATABRICKS_WAREHOUSE_ID environment variable
        2. config.sql_warehouse.warehouse_id from app.yaml
        3. resources[0].warehouse_id from app.yaml (fallback)
        """
        # Check environment variable first
        env_warehouse = os.getenv("DATABRICKS_WAREHOUSE_ID")
        if env_warehouse:
            return env_warehouse

        # Check config section
        config_warehouse = self.config.get("config", {}).get("sql_warehouse", {}).get("warehouse_id")
        if config_warehouse and not config_warehouse.startswith("${"):
            return config_warehouse

        # Fallback to resources section
        resources = self.config.get("resources", [])
        if resources and len(resources) > 0:
            resource_warehouse = resources[0].get("warehouse_id")
            if resource_warehouse:
                return resource_warehouse

        return None

    @property
    def sql_warehouse_http_path(self):
        """
        SQL Warehouse HTTP path from env or config.

        Priority:
        1. DATABRICKS_WAREHOUSE_HTTP_PATH environment variable
        2. config.sql_warehouse.http_path from app.yaml
        3. Auto-construct from warehouse_id if available
        """
        # Check environment variable first
        env_path = os.getenv("DATABRICKS_WAREHOUSE_HTTP_PATH")
        if env_path:
            return env_path

        # Check config section
        config_path = self.config.get("config", {}).get("sql_warehouse", {}).get("http_path")
        if config_path and not config_path.startswith("${"):
            return config_path

        # Auto-construct from warehouse_id
        warehouse_id = self.sql_warehouse_id
        if warehouse_id:
            return f"/sql/1.0/warehouses/{warehouse_id}"

        return None

    @property
    def auth_mode(self):
        return self.config.get("config", {}).get("auth", {}).get("mode", "service_principal")

    @property
    def page_title(self):
        return self.config.get("config", {}).get("ui", {}).get("page_title", "Genify")

    @property
    def page_icon(self):
        return self.config.get("config", {}).get("ui", {}).get("page_icon", "🧞")

    @property
    def layout(self):
        return self.config.get("config", {}).get("ui", {}).get("layout", "wide")

    @property
    def tier1_template_path(self):
        """Path to Tier 1 (Unity Catalog table comment) template."""
        template_path = self.config.get("config", {}).get("templates", {}).get("tier1")
        if template_path:
            return Path(__file__).parent / template_path
        # Default fallback
        return Path(__file__).parent / "templates" / "table_comment_template.yml"

    @property
    def tier2_template_path(self):
        """Path to Tier 2 (Genie space metadata) template."""
        template_path = self.config.get("config", {}).get("templates", {}).get("tier2")
        if template_path:
            return Path(__file__).parent / template_path
        # Default fallback
        return Path(__file__).parent / "templates" / "genie_space_metadata.yml"

    @property
    def tier1_sections_config_path(self):
        """Path to Tier 1 section-based interview config."""
        return Path(__file__).parent / "templates" / "table_comment" / "sections.yaml"

    @property
    def tier2_sections_config_path(self):
        """Path to Tier 2 section-based interview config."""
        return Path(__file__).parent / "templates" / "genie" / "sections.yaml"

    @property
    def prompt_template_path(self):
        """Path to LLM interview prompt template (legacy - combined prompt)."""
        template_path = self.config.get("config", {}).get("templates", {}).get("prompt")
        if template_path:
            return Path(__file__).parent / template_path
        # Default fallback
        return Path(__file__).parent / "prompts" / "schema_generator_prompt.md"

    @property
    def table_comment_prompt_path(self):
        """Path to Phase 1 (table comment) interview prompt."""
        template_path = self.config.get("config", {}).get("templates", {}).get("table_comment_prompt")
        if template_path:
            return Path(__file__).parent / template_path
        # Default fallback
        return Path(__file__).parent / "prompts" / "table_comment_prompt.md"

    @property
    def genie_prompt_path(self):
        """Path to Phase 2 (Genie metadata) interview prompt."""
        template_path = self.config.get("config", {}).get("templates", {}).get("genie_prompt")
        if template_path:
            return Path(__file__).parent / template_path
        # Default fallback
        return Path(__file__).parent / "prompts" / "genie_metadata_prompt.md"

    # === Lakebase Configuration ===
    # PostgreSQL backend for persistent session storage

    @property
    def lakebase_enabled(self) -> bool:
        """
        Check if Lakebase persistence is enabled.

        Priority:
        1. LAKEBASE_ENABLED environment variable (true/false)
        2. config.lakebase.enabled from app.yaml
        """
        env_enabled = os.getenv("LAKEBASE_ENABLED")
        if env_enabled is not None:
            return env_enabled.lower() in ("true", "1", "yes")
        return self.config.get("config", {}).get("lakebase", {}).get("enabled", False)

    @property
    def lakebase_resource_name(self) -> str:
        """
        Lakebase resource name configured in Databricks Apps.

        This is used to look up the connection details from the app context.
        """
        return os.getenv("LAKEBASE_RESOURCE_NAME") or \
               self.config.get("config", {}).get("lakebase", {}).get("resource_name", "genify-lakebase")

    @property
    def lakebase_schema(self) -> str:
        """PostgreSQL schema for session storage."""
        return os.getenv("LAKEBASE_SCHEMA") or \
               self.config.get("config", {}).get("lakebase", {}).get("schema", "genify")

    @property
    def lakebase_table(self) -> str:
        """PostgreSQL table for session storage."""
        return os.getenv("LAKEBASE_TABLE") or \
               self.config.get("config", {}).get("lakebase", {}).get("table", "user_sessions")

    @property
    def lakebase_pool_size(self) -> int:
        """Connection pool size for Lakebase."""
        env_pool = os.getenv("LAKEBASE_POOL_SIZE")
        if env_pool:
            return int(env_pool)
        return self.config.get("config", {}).get("lakebase", {}).get("pool_size", 5)


# Global config instance
config = AppConfig()
