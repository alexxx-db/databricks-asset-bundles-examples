"""
Format table profiles into human-readable text optimized for LLM context.
Generates markdown summaries that help LLMs understand data patterns.
"""


def format_profile_for_llm(profile):
    """
    Format profile data into human-readable markdown optimized for LLM context.

    Args:
        profile: Dict with table-level and column-level statistics from profiler

    Returns:
        Markdown-formatted string ready for LLM consumption
    """
    if not profile:
        return "No profile data available."

    output = []

    # Header
    table_info = profile.get("table", {})
    full_name = table_info.get("full_name", "Unknown Table")
    output.append(f"## Table Profile: {full_name}\n")

    # Table-level statistics
    table_stats = profile.get("table_stats", {})
    if table_stats:
        output.append("### Table Statistics")

        if table_stats.get("row_count") is not None:
            output.append(f"- **Row Count**: {table_stats['row_count']:,} rows")

        if table_stats.get("size_readable"):
            output.append(f"- **Data Size**: {table_stats['size_readable']}")

        if table_stats.get("format"):
            output.append(f"- **Table Format**: {table_stats['format']}")

        if table_stats.get("num_files"):
            output.append(f"- **Number of Files**: {table_stats['num_files']:,}")

        if table_stats.get("last_modified"):
            output.append(f"- **Last Modified**: {table_stats['last_modified']}")

        if table_stats.get("partition_columns"):
            partition_cols = table_stats["partition_columns"]
            if isinstance(partition_cols, list) and partition_cols:
                output.append(f"- **Partitioned By**: {', '.join(partition_cols)}")
            elif isinstance(partition_cols, str) and partition_cols != '[]':
                output.append(f"- **Partitioned By**: {partition_cols}")

        output.append("")  # Empty line

    # Column profiles organized by type
    column_profiles = profile.get("column_profiles", {})
    if column_profiles:
        output.append("### Data Characteristics\n")

        # Group columns by type
        date_columns = []
        categorical_columns = []
        numeric_columns = []
        boolean_columns = []
        other_columns = []

        for col_name, col_profile in column_profiles.items():
            data_type = col_profile.get("type", "").lower()

            if any(t in data_type for t in ['date', 'timestamp']):
                date_columns.append((col_name, col_profile))
            elif any(t in data_type for t in ['string', 'varchar', 'char']):
                categorical_columns.append((col_name, col_profile))
            elif any(t in data_type for t in ['int', 'long', 'bigint', 'double', 'float', 'decimal', 'numeric']):
                numeric_columns.append((col_name, col_profile))
            elif 'boolean' in data_type:
                boolean_columns.append((col_name, col_profile))
            else:
                other_columns.append((col_name, col_profile))

        # Format date columns
        if date_columns:
            output.append("#### Key Date/Timestamp Columns")
            for col_name, col_profile in date_columns:
                stats = col_profile.get("stats", {})

                line = f"- **{col_name}**"
                parts = []

                if stats.get("min_date") and stats.get("max_date"):
                    parts.append(f"{stats['min_date']} to {stats['max_date']}")
                    if stats.get("range_days") is not None:
                        parts.append(f"({stats['range_days']:,} days of data)")

                if stats.get("days_since_last") is not None:
                    days = stats["days_since_last"]
                    if days == 0:
                        parts.append("(updated today)")
                    elif days == 1:
                        parts.append("(last updated yesterday)")
                    else:
                        parts.append(f"(last updated {days} days ago)")

                if stats.get("null_percentage") is not None and stats["null_percentage"] > 0:
                    parts.append(f"{stats['null_percentage']}% NULL")

                if parts:
                    line += ": " + ", ".join(parts)

                output.append(line)

            output.append("")  # Empty line

        # Format categorical columns with top values
        if categorical_columns:
            categorical_with_values = [
                (col_name, col_profile)
                for col_name, col_profile in categorical_columns
                if col_profile.get("stats", {}).get("top_values")
            ]

            if categorical_with_values:
                output.append("#### Important Categorical Columns")

                for col_name, col_profile in categorical_with_values:
                    stats = col_profile.get("stats", {})
                    top_values = stats.get("top_values", [])

                    if top_values:
                        distinct_count = stats.get("distinct_count")
                        if distinct_count:
                            output.append(f"- **{col_name}** ({distinct_count:,} distinct values):")
                        else:
                            output.append(f"- **{col_name}**:")

                        for val_info in top_values[:10]:  # Limit to top 10
                            value = val_info.get("value", "NULL")
                            count = val_info.get("count", 0)
                            percentage = val_info.get("percentage", 0)
                            output.append(f"  * {value}: {percentage}% ({count:,} rows)")

                output.append("")  # Empty line

        # Format numeric columns
        if numeric_columns:
            output.append("#### Numeric Columns")

            for col_name, col_profile in numeric_columns:
                stats = col_profile.get("stats", {})

                line = f"- **{col_name}**"
                parts = []

                if stats.get("min") is not None and stats.get("max") is not None:
                    min_val = stats["min"]
                    max_val = stats["max"]

                    # Format numbers nicely
                    if isinstance(min_val, (int, float)) and isinstance(max_val, (int, float)):
                        if min_val == int(min_val) and max_val == int(max_val):
                            parts.append(f"Range: {int(min_val):,} to {int(max_val):,}")
                        else:
                            parts.append(f"Range: {min_val:,.2f} to {max_val:,.2f}")

                if stats.get("avg") is not None:
                    avg_val = stats["avg"]
                    if isinstance(avg_val, (int, float)):
                        parts.append(f"Avg: {avg_val:,.2f}")

                if stats.get("distinct_count"):
                    parts.append(f"{stats['distinct_count']:,} distinct values")

                if stats.get("null_percentage") is not None and stats["null_percentage"] > 0:
                    parts.append(f"{stats['null_percentage']}% NULL")

                if parts:
                    line += ": " + ", ".join(parts)

                output.append(line)

            output.append("")  # Empty line

        # Format boolean columns
        if boolean_columns:
            output.append("#### Boolean Columns")

            for col_name, col_profile in boolean_columns:
                stats = col_profile.get("stats", {})
                distribution = stats.get("distribution", {})

                if distribution:
                    line = f"- **{col_name}**: "
                    parts = []
                    for value, info in distribution.items():
                        count = info.get("count", 0)
                        percentage = info.get("percentage", 0)
                        parts.append(f"{value} ({percentage}% - {count:,} rows)")
                    line += ", ".join(parts)
                    output.append(line)

            output.append("")  # Empty line

        # Format data completeness summary
        completeness_data = []
        for col_name, col_profile in column_profiles.items():
            stats = col_profile.get("stats", {})
            completeness = stats.get("completeness")
            null_pct = stats.get("null_percentage")

            if null_pct is not None and null_pct > 0:
                completeness_data.append((col_name, completeness or (100 - null_pct), null_pct))

        if completeness_data:
            # Sort by completeness descending
            completeness_data.sort(key=lambda x: x[1], reverse=True)

            output.append("#### Data Completeness")
            for col_name, completeness, null_pct in completeness_data[:10]:  # Top 10
                if null_pct > 10:  # Only show if significant nulls
                    output.append(f"- **{col_name}**: {completeness:.1f}% complete ({null_pct:.1f}% NULL)")

            output.append("")  # Empty line

    return "\n".join(output)


def format_profile_for_display(profile):
    """
    Format profile for display in Streamlit UI (may include more details than LLM version).

    Args:
        profile: Dict with table-level and column-level statistics

    Returns:
        Markdown-formatted string for UI display
    """
    # For now, use the same formatter as LLM
    # Can be extended later with more UI-specific formatting
    return format_profile_for_llm(profile)


def get_profile_summary_stats(profile):
    """
    Extract key summary statistics from profile for quick display.

    Args:
        profile: Dict with table-level and column-level statistics

    Returns:
        Dict with summary metrics
    """
    summary = {}

    table_stats = profile.get("table_stats", {})
    column_profiles = profile.get("column_profiles", {})

    # Table-level summary
    summary["row_count"] = table_stats.get("row_count")
    summary["size_readable"] = table_stats.get("size_readable")
    summary["table_format"] = table_stats.get("format")

    # Column counts by type
    summary["total_columns"] = len(column_profiles)
    summary["date_columns"] = 0
    summary["categorical_columns"] = 0
    summary["numeric_columns"] = 0

    for col_profile in column_profiles.values():
        data_type = col_profile.get("type", "").lower()
        if any(t in data_type for t in ['date', 'timestamp']):
            summary["date_columns"] += 1
        elif any(t in data_type for t in ['string', 'varchar']):
            summary["categorical_columns"] += 1
        elif any(t in data_type for t in ['int', 'long', 'double', 'float', 'decimal']):
            summary["numeric_columns"] += 1

    return summary
