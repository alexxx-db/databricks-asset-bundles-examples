"""
Unity Catalog Information Schema queries.

References:
- Information Schema Overview: https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-information-schema
- Available Views: https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-information-schema#information-schema-views
- Cookbook Pattern: https://apps-cookbook.dev/docs/streamlit/tables/tables_read

Key Implementation Notes (from Databricks docs):
1. Automatic privilege filtering: system.information_schema automatically filters results to show
   only objects you have Unity Catalog privileges to access. This is different from other system tables.

2. Performance: Always use selective filters (WHERE table_catalog = 'x' AND table_schema = 'y')
   to prevent query timeouts. LIMIT pushdown is NOT supported - use WHERE clauses for filtering.

3. Lowercase identifiers: All identifiers (except column/tag names) are stored as lowercase STRING.
   Compare directly without LOWER() or UPPER() functions for better performance.

4. Manual sync: Some catalog metadata changes may require REPAIR TABLE to reflect in information_schema.

Information Schema Views Used:
- system.information_schema.catalogs: Lists all accessible catalogs
- system.information_schema.schemata: Lists schemas within catalogs
- system.information_schema.tables: Lists tables and views with metadata
- system.information_schema.columns: Lists columns with types and comments
"""


def list_catalogs(connection):
    """
    List all accessible catalogs.

    Args:
        connection: Databricks SQL connection

    Returns:
        List of tuples: (catalog_name, catalog_owner, comment, created)
    """
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT catalog_name, catalog_owner, comment, created
            FROM system.information_schema.catalogs
            ORDER BY catalog_name
        """)
        return cursor.fetchall()


def list_schemas(connection, catalog):
    """
    List schemas in a catalog.

    Args:
        connection: Databricks SQL connection
        catalog: Catalog name

    Returns:
        List of tuples: (schema_name, schema_owner, comment)
    """
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT schema_name, schema_owner, comment
            FROM system.information_schema.schemata
            WHERE catalog_name = ?
            ORDER BY schema_name
        """, [catalog.lower()])
        return cursor.fetchall()


def list_tables(connection, catalog, schema):
    """
    List tables with metadata.

    Args:
        connection: Databricks SQL connection
        catalog: Catalog name
        schema: Schema name

    Returns:
        List of tuples: (table_name, table_type, comment, created_by, last_altered, data_source_format)
    """
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                table_name,
                table_type,
                comment,
                created_by,
                last_altered,
                data_source_format
            FROM system.information_schema.tables
            WHERE table_catalog = ?
              AND table_schema = ?
            ORDER BY table_name
        """, [catalog.lower(), schema.lower()])
        return cursor.fetchall()


def get_table_columns(connection, catalog, schema, table):
    """
    Get columns with types and existing comments.

    Args:
        connection: Databricks SQL connection
        catalog: Catalog name
        schema: Schema name
        table: Table name

    Returns:
        List of tuples: (column_name, data_type, comment, ordinal_position, is_nullable)
    """
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                column_name,
                data_type,
                comment,
                ordinal_position,
                is_nullable
            FROM system.information_schema.columns
            WHERE table_catalog = ?
              AND table_schema = ?
              AND table_name = ?
            ORDER BY ordinal_position
        """, [catalog.lower(), schema.lower(), table.lower()])
        return cursor.fetchall()


def get_table_metadata(connection, catalog, schema, table):
    """
    Get comprehensive table metadata.

    Args:
        connection: Databricks SQL connection
        catalog: Catalog name
        schema: Schema name
        table: Table name

    Returns:
        Tuple: (table_name, table_type, comment, created, created_by, last_altered, last_altered_by, data_source_format)
    """
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                table_name,
                table_type,
                comment,
                created,
                created_by,
                last_altered,
                last_altered_by,
                data_source_format
            FROM system.information_schema.tables
            WHERE table_catalog = ?
              AND table_schema = ?
              AND table_name = ?
        """, [catalog.lower(), schema.lower(), table.lower()])
        return cursor.fetchone()


def build_table_context(connection, catalog, schema, table):
    """
    Build comprehensive table context for LLM interview.

    Args:
        connection: Databricks SQL connection
        catalog: Catalog name
        schema: Schema name
        table: Table name

    Returns:
        Dict with table metadata and columns
    """
    metadata = get_table_metadata(connection, catalog, schema, table)
    columns = get_table_columns(connection, catalog, schema, table)

    if not metadata:
        return None

    return {
        "catalog": catalog,
        "schema": schema,
        "table": table,
        "table_type": metadata[1] if metadata else None,
        "existing_comment": metadata[2] if metadata else None,
        "created": str(metadata[3]) if metadata and metadata[3] else None,
        "created_by": metadata[4] if metadata else None,
        "last_altered": str(metadata[5]) if metadata and metadata[5] else None,
        "last_altered_by": metadata[6] if metadata else None,
        "data_format": metadata[7] if metadata else None,
        "columns": [
            {
                "name": col[0],
                "type": col[1],
                "comment": col[2],
                "position": col[3],
                "nullable": col[4]
            }
            for col in columns
        ]
    }


def get_columns_for_table(connection, catalog, schema, table):
    """
    Get columns in a format suitable for profiling.

    Args:
        connection: Databricks SQL connection
        catalog: Catalog name
        schema: Schema name
        table: Table name

    Returns:
        List of dicts with 'name' and 'type' keys
    """
    columns = get_table_columns(connection, catalog, schema, table)
    return [
        {"name": col[0], "type": col[1]}
        for col in columns
    ]
