"""
Abstract backend interface for state storage.
"""
from abc import ABC, abstractmethod
from typing import Any, List


class StateBackend(ABC):
    """Abstract backend for state storage."""

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value by key."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Set a value by key."""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete a key."""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass

    @abstractmethod
    def keys_with_prefix(self, prefix: str) -> List[str]:
        """Get all keys with given prefix."""
        pass

    @abstractmethod
    def clear_prefix(self, prefix: str) -> int:
        """Delete all keys with prefix, return count deleted."""
        pass
