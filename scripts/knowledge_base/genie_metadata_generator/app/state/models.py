"""
Data models for state management.
"""
from dataclasses import dataclass
from typing import Dict


@dataclass
class TableIdentifier:
    """Unique identifier for a table in Unity Catalog."""
    catalog: str
    schema: str
    table: str
    
    @property
    def full_name(self) -> str:
        """Get fully qualified table name."""
        return f"{self.catalog}.{self.schema}.{self.table}"
    
    @property
    def key(self) -> str:
        """Get unique key for storage."""
        return f"{self.catalog}_{self.schema}_{self.table}"
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "TableIdentifier":
        """Create from dictionary."""
        return cls(
            catalog=data['catalog'],
            schema=data['schema'],
            table=data['table']
        )
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary."""
        return {
            'catalog': self.catalog,
            'schema': self.schema,
            'table': self.table
        }
