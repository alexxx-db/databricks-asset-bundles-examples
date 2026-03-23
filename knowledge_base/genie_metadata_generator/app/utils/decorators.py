"""Utility decorators for common patterns."""
import logging
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


def require_lakebase(default_return: Any = None):
    """
    Decorator to check Lakebase availability before executing function.

    Usage:
        @require_lakebase(default_return=None)
        def my_function():
            # This only runs if Lakebase is enabled
            pass

    Args:
        default_return: Value to return if Lakebase not available

    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from config import config
            if not config.lakebase_enabled:
                logger.warning(f"Cannot {func.__name__}: Lakebase not enabled")
                return default_return
            return func(*args, **kwargs)
        return wrapper
    return decorator


def log_errors(logger_instance: logging.Logger, default_return: Any = None, reraise: bool = False):
    """
    Decorator to log exceptions with consistent format.

    Usage:
        @log_errors(logger, default_return=None, reraise=True)
        def my_function():
            # Errors will be logged and optionally reraised
            pass

    Args:
        logger_instance: Logger to use for error logging
        default_return: Value to return on error (if not reraising)
        reraise: Whether to reraise the exception after logging

    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger_instance.error(f"Failed to {func.__name__}: {e}", exc_info=True)
                if reraise:
                    raise
                return default_return
        return wrapper
    return decorator
