"""
Service Principal authentication for Databricks SQL Warehouse connections.
Reference: https://apps-cookbook.dev/docs/streamlit/tables/tables_read

When running in Databricks Apps, these environment variables are automatically available:
- DATABRICKS_HOST: Workspace URL (auto-provided)
- DATABRICKS_CLIENT_ID: Service principal app ID (auto-provided)
- DATABRICKS_CLIENT_SECRET: Service principal secret (auto-provided)
- DATABRICKS_WAREHOUSE_ID: SQL Warehouse ID (from app.yaml or set manually)

See: https://docs.databricks.com/aws/en/dev-tools/databricks-apps/system-env#default-environment-variables
"""

from databricks import sql
from databricks.sdk.core import Config
import streamlit as st


@st.cache_resource(ttl=300, show_spinner="Connecting to Databricks...")
def get_connection():
    """
    Create authenticated connection using service principal.
    
    Uses Databricks SDK Config for automatic credential handling.
    Reference: https://apps-cookbook.dev/docs/streamlit/tables/tables_read
    
    Environment variables (automatically available in Databricks Apps):
    - DATABRICKS_HOST: Workspace URL (auto-set by Databricks Apps)
    - DATABRICKS_CLIENT_ID: Service principal app ID (auto-set by Databricks Apps)
    - DATABRICKS_CLIENT_SECRET: Service principal secret (auto-set by Databricks Apps)
    - DATABRICKS_WAREHOUSE_ID: SQL Warehouse ID (optional - can read from app.yaml)
    
    For local development, set these manually in .env file.
    
    Returns:
        Connection object for executing SQL queries
        
    Note:
        Connection is cached for 5 minutes (300 seconds) to avoid stale connections
        while maintaining performance across users and sessions.
    """
    # Use Databricks SDK Config for automatic credential handling
    cfg = Config()
    
    # Get warehouse_id from environment or app.yaml config
    from config import config
    warehouse_id = config.sql_warehouse_id
    
    if not warehouse_id:
        raise ValueError(
            "SQL Warehouse ID not configured.\n\n"
            "Set DATABRICKS_WAREHOUSE_ID environment variable or "
            "configure 'sql_warehouse.warehouse_id' in app.yaml\n\n"
            "See: app/WAREHOUSE_CONFIG.md for details"
        )
    
    # Build http_path
    http_path = f"/sql/1.0/warehouses/{warehouse_id}"
    
    # Connect using SDK Config (handles authentication automatically)
    return sql.connect(
        server_hostname=cfg.host,
        http_path=http_path,
        credentials_provider=lambda: cfg.authenticate,
    )


def get_sql_connection():
    """
    Alias for get_connection() for compatibility.
    
    Returns:
        Connection object for executing SQL queries
    """
    return get_connection()
