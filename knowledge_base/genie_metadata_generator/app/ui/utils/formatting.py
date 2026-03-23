"""
UI formatting utilities for consistent display across the application.

Provides standard formatters for common UI elements like counts, timestamps,
queue status, and time estimates.
"""


def format_table_count(count: int, suffix: str = "table") -> str:
    """
    Format table count with proper pluralization.

    Args:
        count: Number of tables
        suffix: Singular form of the item (default: "table")

    Returns:
        Formatted string like "1 table" or "5 tables"

    Examples:
        >>> format_table_count(1)
        '1 table'
        >>> format_table_count(5)
        '5 tables'
        >>> format_table_count(0)
        '0 tables'
    """
    plural = suffix if count == 1 else f"{suffix}s"
    return f"{count} {plural}"


def format_queue_status(count: int) -> str:
    """
    Format queue count consistently.

    Args:
        count: Number of tables in queue

    Returns:
        Formatted string like "5 tables in queue"

    Examples:
        >>> format_queue_status(0)
        '0 tables in queue'
        >>> format_queue_status(1)
        '1 table in queue'
        >>> format_queue_status(10)
        '10 tables in queue'
    """
    return f"{format_table_count(count)} in queue"


def format_completed_status(count: int) -> str:
    """
    Format completed count consistently.

    Args:
        count: Number of completed tables

    Returns:
        Formatted string like "5 tables documented"

    Examples:
        >>> format_completed_status(1)
        '1 table documented'
        >>> format_completed_status(10)
        '10 tables documented'
    """
    return f"{format_table_count(count)} documented"


def format_time_estimate(table_count: int, has_profiles: bool = True) -> str:
    """
    Format time estimate for documentation workflow.

    Args:
        table_count: Number of tables to document
        has_profiles: Whether tables have data profiles (default: True)

    Returns:
        Formatted time estimate like "~15 minutes"

    Examples:
        >>> format_time_estimate(5, has_profiles=True)
        '~15 minutes'
        >>> format_time_estimate(5, has_profiles=False)
        '~25 minutes'
        >>> format_time_estimate(1, has_profiles=True)
        '~3 minutes'
    """
    # Average time per table: 3 minutes with profile, 5 without
    avg_time = 3 if has_profiles else 5
    total_time = table_count * avg_time

    if total_time == 0:
        return "~0 minutes"
    elif total_time == 1:
        return "~1 minute"
    else:
        return f"~{total_time} minutes"


def format_profile_status(has_profile: bool) -> str:
    """
    Format profile status consistently.

    Args:
        has_profile: Whether profile exists

    Returns:
        Formatted status like "✓ Profiled" or "No profile"

    Examples:
        >>> format_profile_status(True)
        '✓ Profiled'
        >>> format_profile_status(False)
        'No profile'
    """
    return "✓ Profiled" if has_profile else "No profile"


def format_percentage(current: int, total: int) -> str:
    """
    Format percentage for progress indicators.

    Args:
        current: Current count
        total: Total count

    Returns:
        Formatted percentage like "50%"

    Examples:
        >>> format_percentage(5, 10)
        '50%'
        >>> format_percentage(0, 10)
        '0%'
        >>> format_percentage(10, 10)
        '100%'
    """
    if total == 0:
        return "0%"

    percentage = int((current / total) * 100)
    return f"{percentage}%"


def format_section_progress(current: int, total: int) -> str:
    """
    Format section progress for interviews.

    Args:
        current: Current section number (0-indexed)
        total: Total number of sections

    Returns:
        Formatted progress like "Section 3 of 5"

    Examples:
        >>> format_section_progress(2, 5)
        'Section 3 of 5'
        >>> format_section_progress(0, 5)
        'Section 1 of 5'
    """
    return f"Section {current + 1} of {total}"


def format_timestamp(timestamp: str, format_type: str = "date") -> str:
    """
    Format timestamp for consistent display.

    Args:
        timestamp: ISO format timestamp string
        format_type: Type of formatting ("date", "datetime", "time")

    Returns:
        Formatted timestamp

    Examples:
        >>> format_timestamp("2026-02-01T14:30:00", "date")
        '2026-02-01'
        >>> format_timestamp("2026-02-01T14:30:00", "datetime")
        '2026-02-01 14:30'
    """
    if not timestamp:
        return "Unknown"

    if format_type == "date":
        # Return just date part
        return timestamp[:10]
    elif format_type == "datetime":
        # Return date and time without seconds
        return timestamp[:16].replace('T', ' ')
    elif format_type == "time":
        # Return just time part
        return timestamp[11:16] if len(timestamp) > 11 else ""
    else:
        return timestamp


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size like "1.5 KB" or "2.3 MB"

    Examples:
        >>> format_file_size(1024)
        '1.0 KB'
        >>> format_file_size(1536)
        '1.5 KB'
        >>> format_file_size(1048576)
        '1.0 MB'
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        kb = size_bytes / 1024
        return f"{kb:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        mb = size_bytes / (1024 * 1024)
        return f"{mb:.1f} MB"
    else:
        gb = size_bytes / (1024 * 1024 * 1024)
        return f"{gb:.1f} GB"


def format_full_table_name(catalog: str, schema: str, table: str) -> str:
    """
    Format full table name consistently.

    Args:
        catalog: Catalog name
        schema: Schema name
        table: Table name

    Returns:
        Formatted full table name like "catalog.schema.table"

    Examples:
        >>> format_full_table_name("main", "sales", "orders")
        'main.sales.orders'
    """
    return f"{catalog}.{schema}.{table}"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length with suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length before truncation
        suffix: Suffix to add when truncated (default: "...")

    Returns:
        Truncated text with suffix if needed

    Examples:
        >>> truncate_text("Short text", 100)
        'Short text'
        >>> truncate_text("Very long text that exceeds the limit", 20)
        'Very long text th...'
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix
