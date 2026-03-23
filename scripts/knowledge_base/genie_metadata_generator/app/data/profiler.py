"""
Lightweight data profiler for Databricks tables.
Leverages cached statistics and smart sampling for performance.

References:
- DESCRIBE DETAIL: https://docs.databricks.com/sql/language-manual/sql-ref-syntax-aux-describe-table.html
- Table Statistics: https://docs.databricks.com/optimizations/table-statistics.html
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def get_table_profile(connection, catalog, schema, table, columns):
    """
    Generate comprehensive lightweight table profile.

    Args:
        connection: Databricks SQL connection
        catalog: Catalog name
        schema: Schema name
        table: Table name
        columns: List of column dicts with 'name' and 'type'

    Returns:
        Dict with table-level and column-level statistics
    """
    full_name = f"`{catalog}`.`{schema}`.`{table}`"

    profile = {
        "table": {
            "full_name": f"{catalog}.{schema}.{table}",
            "catalog": catalog,
            "schema": schema,
            "table": table
        },
        "table_stats": {},
        "column_profiles": {}
    }

    # Get table-level statistics
    profile["table_stats"] = _get_table_statistics(connection, full_name, catalog, schema, table)

    # Get column-level profiles
    for col in columns:
        col_profile = _profile_column(
            connection,
            full_name,
            col['name'],
            col['type'],
            profile["table_stats"].get("row_count")
        )
        if col_profile:
            profile["column_profiles"][col['name']] = col_profile

    return profile


def get_table_statistics(connection, catalog, schema, table):
    """
    Get basic table statistics (public wrapper for _get_table_statistics).

    Args:
        connection: Databricks SQL connection
        catalog: Catalog name
        schema: Schema name
        table: Table name

    Returns:
        Dict with table-level stats (row_count, size_bytes, format, etc.)
    """
    full_name = f"`{catalog}`.`{schema}`.`{table}`"
    return _get_table_statistics(connection, full_name, catalog, schema, table)


def _get_table_statistics(connection, full_name, catalog, schema, table):
    """
    Get table-level statistics using DESCRIBE DETAIL and cached stats.

    Args:
        connection: Databricks SQL connection
        full_name: Fully qualified table name with backticks
        catalog: Catalog name
        schema: Schema name
        table: Table name

    Returns:
        Dict with table-level stats
    """
    stats = {}
    with connection.cursor() as cursor:
        try:
            # Try DESCRIBE DETAIL (works for Delta tables)
            cursor.execute(f"DESCRIBE DETAIL {full_name}")
            detail = cursor.fetchone()

            if detail:
                # Extract relevant fields (column order may vary)
                col_names = [desc[0].lower() for desc in cursor.description]
                detail_dict = dict(zip(col_names, detail, strict=False))

                stats["format"] = detail_dict.get("format", "UNKNOWN")
                stats["row_count"] = detail_dict.get("numrows") or detail_dict.get("num_rows")
                stats["size_bytes"] = detail_dict.get("sizeinbytes") or detail_dict.get("size_bytes")
                stats["num_files"] = detail_dict.get("numfiles") or detail_dict.get("num_files")
                stats["last_modified"] = detail_dict.get("lastmodified") or detail_dict.get("last_modified")
                stats["partition_columns"] = detail_dict.get("partitioncolumns") or detail_dict.get("partition_columns")

                # Format size for readability
                if stats["size_bytes"]:
                    stats["size_readable"] = _format_bytes(stats["size_bytes"])

        except Exception as e:
            # DESCRIBE DETAIL might not work for non-Delta tables
            logger.warning(f"Could not get detailed table stats: {e}")
            stats["errors"] = stats.get("errors", []) + [f"DESCRIBE DETAIL failed: {str(e)}"]

        # Fallback: Get row count if not available
        if not stats.get("row_count"):
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {full_name}")
                stats["row_count"] = cursor.fetchone()[0]
            except Exception as e:
                logger.warning(f"Could not get row count: {e}")
                stats["errors"] = stats.get("errors", []) + [f"Row count failed: {str(e)}"]
                stats["row_count"] = None

    return stats


def _profile_column(connection, full_name, column_name, data_type, total_rows):
    """
    Profile a single column based on its data type.

    Args:
        connection: Databricks SQL connection
        full_name: Fully qualified table name
        column_name: Column name
        data_type: Column data type
        total_rows: Total row count for percentage calculations

    Returns:
        Dict with column statistics
    """
    data_type_lower = data_type.lower()
    profile = {
        "type": data_type,
        "stats": {}
    }

    with connection.cursor() as cursor:
        try:
            # Get null percentage (works for all types)
            cursor.execute(f"""
                SELECT
                    COUNT(*) as total_count,
                    SUM(CASE WHEN `{column_name}` IS NULL THEN 1 ELSE 0 END) as null_count
                FROM {full_name}
            """)
            result = cursor.fetchone()
            if result:
                total_count = result[0]
                null_count = result[1]
                if total_count > 0:
                    profile["stats"]["null_percentage"] = round((null_count / total_count) * 100, 2)
                    profile["stats"]["completeness"] = round(((total_count - null_count) / total_count) * 100, 2)

            # Type-specific profiling
            if any(t in data_type_lower for t in ['string', 'varchar', 'char']):
                profile["stats"].update(_profile_string_column(cursor, full_name, column_name, total_rows))

            elif any(t in data_type_lower for t in ['int', 'long', 'bigint', 'double', 'float', 'decimal', 'numeric']):
                profile["stats"].update(_profile_numeric_column(cursor, full_name, column_name))

            elif any(t in data_type_lower for t in ['date', 'timestamp']):
                profile["stats"].update(_profile_date_column(cursor, full_name, column_name))

            elif 'boolean' in data_type_lower:
                profile["stats"].update(_profile_boolean_column(cursor, full_name, column_name))

        except Exception as e:
            profile["stats"]["error"] = f"Profiling failed: {str(e)}"

    return profile


def _profile_string_column(cursor, full_name, column_name, total_rows):
    """Profile string/categorical column."""
    stats = {}

    try:
        # Get approximate distinct count
        cursor.execute(f"""
            SELECT APPROX_COUNT_DISTINCT(`{column_name}`) as distinct_count
            FROM {full_name}
        """)
        result = cursor.fetchone()
        if result:
            distinct_count = result[0]
            stats["distinct_count"] = distinct_count

            # Only get top values if cardinality is reasonable (< 1000)
            if distinct_count and distinct_count < 1000:
                stats["top_values"] = _get_top_values(cursor, full_name, column_name, limit=10)

    except Exception as e:
        stats["error"] = f"String profiling failed: {str(e)}"

    return stats


def _profile_numeric_column(cursor, full_name, column_name):
    """Profile numeric column."""
    stats = {}

    try:
        cursor.execute(f"""
            SELECT
                MIN(`{column_name}`) as min_val,
                MAX(`{column_name}`) as max_val,
                AVG(`{column_name}`) as avg_val,
                APPROX_COUNT_DISTINCT(`{column_name}`) as distinct_count
            FROM {full_name}
            WHERE `{column_name}` IS NOT NULL
        """)
        result = cursor.fetchone()
        if result:
            stats["min"] = result[0]
            stats["max"] = result[1]
            stats["avg"] = round(result[2], 2) if result[2] else None
            stats["distinct_count"] = result[3]

    except Exception as e:
        stats["error"] = f"Numeric profiling failed: {str(e)}"

    return stats


def _profile_date_column(cursor, full_name, column_name):
    """Profile date/timestamp column."""
    stats = {}

    try:
        cursor.execute(f"""
            SELECT
                MIN(`{column_name}`) as min_date,
                MAX(`{column_name}`) as max_date
            FROM {full_name}
            WHERE `{column_name}` IS NOT NULL
        """)
        result = cursor.fetchone()
        if result and result[0] and result[1]:
            min_date = result[0]
            max_date = result[1]

            stats["min_date"] = str(min_date)
            stats["max_date"] = str(max_date)

            # Calculate date range in days
            if isinstance(min_date, (datetime, str)) and isinstance(max_date, (datetime, str)):
                try:
                    if isinstance(min_date, str):
                        min_date = datetime.fromisoformat(str(min_date).replace('Z', '+00:00'))
                    if isinstance(max_date, str):
                        max_date = datetime.fromisoformat(str(max_date).replace('Z', '+00:00'))

                    date_range = (max_date - min_date).days
                    stats["range_days"] = date_range

                    # Calculate recency
                    now = datetime.now()
                    if max_date.tzinfo:
                        now = now.astimezone(max_date.tzinfo)
                    days_since_last = (now - max_date).days
                    stats["days_since_last"] = days_since_last
                except Exception as e:
                    logger.debug("Could not compute date range stats: %s", e)

    except Exception as e:
        stats["error"] = f"Date profiling failed: {str(e)}"

    return stats


def _profile_boolean_column(cursor, full_name, column_name):
    """Profile boolean column."""
    stats = {}

    try:
        cursor.execute(f"""
            SELECT
                `{column_name}`,
                COUNT(*) as count
            FROM {full_name}
            WHERE `{column_name}` IS NOT NULL
            GROUP BY `{column_name}`
        """)
        results = cursor.fetchall()

        distribution = {}
        total = 0
        for row in results:
            value = row[0]
            count = row[1]
            distribution[str(value)] = count
            total += count

        # Calculate percentages
        if total > 0:
            stats["distribution"] = {
                k: {"count": v, "percentage": round((v / total) * 100, 1)}
                for k, v in distribution.items()
            }

    except Exception as e:
        stats["error"] = f"Boolean profiling failed: {str(e)}"

    return stats


def _get_top_values(cursor, full_name, column_name, limit=10):
    """
    Get top N most frequent values for a categorical column.

    Args:
        cursor: Database cursor
        full_name: Fully qualified table name
        column_name: Column name
        limit: Number of top values to return

    Returns:
        List of dicts with value, count, and percentage
    """
    try:
        cursor.execute(f"""
            SELECT
                `{column_name}` as value,
                COUNT(*) as count
            FROM {full_name}
            WHERE `{column_name}` IS NOT NULL
            GROUP BY `{column_name}`
            ORDER BY count DESC
            LIMIT {limit}
        """)
        results = cursor.fetchall()

        # Calculate total for percentages
        total = sum(row[1] for row in results)

        top_values = []
        for row in results:
            value = row[0]
            count = row[1]
            top_values.append({
                "value": str(value),
                "count": count,
                "percentage": round((count / total) * 100, 1) if total > 0 else 0
            })

        return top_values

    except Exception as e:
        logger.debug("Could not get top values for column: %s", e)
        return []


def _format_bytes(bytes_val):
    """Format bytes into human-readable size."""
    try:
        bytes_val = float(bytes_val)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} PB"
    except Exception as e:
        logger.debug("Could not format bytes value: %s", e)
        return None
