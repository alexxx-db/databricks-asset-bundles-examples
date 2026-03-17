"""
iceberg_catalog
===============
Production utilities for managing the shared Iceberg catalog layer
(Snowflake Open Catalog / Polaris ↔ Databricks Unity Catalog).

Public API
----------
PolarisClient          - Iceberg REST Catalog client (namespace + table ops)
IcebergSchemaSync      - compare UC ↔ Polaris schemas, detect drift
IcebergTableRegistrar  - register Databricks-authored tables in Snowflake
SnowflakeRefreshClient - trigger Snowflake REFRESH for Databricks-written snapshots
"""

from iceberg_catalog.polaris_client import PolarisClient
from iceberg_catalog.schema_sync import IcebergSchemaSync, SchemaDrift
from iceberg_catalog.table_migration import IcebergTableRegistrar, TableLocation
from iceberg_catalog.snowflake_refresh import SnowflakeRefreshClient

__all__ = [
    "PolarisClient",
    "IcebergSchemaSync",
    "SchemaDrift",
    "IcebergTableRegistrar",
    "TableLocation",
    "SnowflakeRefreshClient",
]

__version__ = "0.1.0"
