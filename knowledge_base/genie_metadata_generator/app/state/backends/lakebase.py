"""
Lakebase PostgreSQL backend for persistent session storage.

This backend enables:
1. Session persistence across browser refreshes
2. Resume functionality when users return
3. Multi-device session continuity
4. Audit trail for debugging

Lakebase is a PostgreSQL database accessible from Databricks Apps.
See: https://apps-cookbook.dev/docs/fastapi/building_endpoints/lakebase/
"""
import json
import logging
from typing import Any, List, Optional
from datetime import datetime
from .base import StateBackend

from utils.sql_identifiers import validate_identifier

logger = logging.getLogger(__name__)


class LakebaseBackend(StateBackend):
    """
    PostgreSQL backend using Lakebase for persistent state.
    
    All operations are synchronous (using psycopg2) to work seamlessly
    with Streamlit's synchronous execution model.
    """
    
    def __init__(self, connection, session_key: str, user_email: str, schema: str = "genify", table: str = "user_sessions"):
        """
        Initialize Lakebase backend.
        
        Args:
            connection: psycopg2 connection object
            session_key: Unique session identifier (email_hash_timestamp)
            user_email: User's email for session queries
            schema: PostgreSQL schema name
            table: PostgreSQL table name
        """
        self.conn = connection
        self.session_key = session_key
        self.user_email = user_email
        self.schema = validate_identifier(schema, "schema")
        self.table = validate_identifier(table, "table")
        self.full_table = f"{self.schema}.{self.table}"
        
        # Ensure table exists on initialization
        self._ensure_table_exists()
        
        logger.info(f"LakebaseBackend initialized for session {session_key[:16]}...")
    
    def _ensure_table_exists(self) -> None:
        """Create the sessions table if it doesn't exist."""
        try:
            with self.conn.cursor() as cur:
                # Create schema if not exists
                cur.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema}")
                
                # Create table with proper indexes
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.full_table} (
                        id SERIAL PRIMARY KEY,
                        session_key VARCHAR(64) NOT NULL,
                        user_email VARCHAR(255) NOT NULL,
                        state_key VARCHAR(512) NOT NULL,
                        value JSONB NOT NULL,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW(),
                        UNIQUE(session_key, state_key)
                    )
                """)
                
                # Create indexes for efficient queries
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.table}_email 
                    ON {self.full_table}(user_email)
                """)
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.table}_session 
                    ON {self.full_table}(session_key)
                """)
                
                self.conn.commit()
                logger.info(f"Ensured table {self.full_table} exists")
        except Exception as e:
            logger.error(f"Error creating table: {e}")
            self.conn.rollback()
            raise
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value by key from the database."""
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    f"SELECT value FROM {self.full_table} WHERE session_key = %s AND state_key = %s",
                    (self.session_key, key)
                )
                row = cur.fetchone()
                if row:
                    return row[0]  # JSONB is auto-converted to Python dict
                return default
        except Exception as e:
            logger.error(f"Error getting key {key}: {e}")
            return default
    
    def set(self, key: str, value: Any) -> None:
        """Set a value by key in the database (upsert)."""
        try:
            # Convert value to JSON-serializable format
            json_value = json.dumps(value, default=str)
            
            with self.conn.cursor() as cur:
                cur.execute(f"""
                    INSERT INTO {self.full_table} (session_key, user_email, state_key, value, updated_at)
                    VALUES (%s, %s, %s, %s::jsonb, NOW())
                    ON CONFLICT (session_key, state_key) 
                    DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
                """, (self.session_key, self.user_email, key, json_value))
                
                self.conn.commit()
                logger.debug(f"Set key {key} for session {self.session_key[:16]}...")
        except Exception as e:
            logger.error(f"Error setting key {key}: {e}")
            self.conn.rollback()
            raise
    
    def delete(self, key: str) -> None:
        """Delete a key from the database."""
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM {self.full_table} WHERE session_key = %s AND state_key = %s",
                    (self.session_key, key)
                )
                self.conn.commit()
                logger.debug(f"Deleted key {key}")
        except Exception as e:
            logger.error(f"Error deleting key {key}: {e}")
            self.conn.rollback()
    
    def exists(self, key: str) -> bool:
        """Check if key exists in the database."""
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    f"SELECT 1 FROM {self.full_table} WHERE session_key = %s AND state_key = %s LIMIT 1",
                    (self.session_key, key)
                )
                return cur.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking existence of key {key}: {e}")
            return False
    
    def keys_with_prefix(self, prefix: str) -> List[str]:
        """Get all keys with given prefix for this session."""
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    f"SELECT state_key FROM {self.full_table} WHERE session_key = %s AND state_key LIKE %s",
                    (self.session_key, f"{prefix}%")
                )
                return [row[0] for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Error getting keys with prefix {prefix}: {e}")
            return []
    
    def clear_prefix(self, prefix: str) -> int:
        """Delete all keys with prefix for this session, return count deleted."""
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM {self.full_table} WHERE session_key = %s AND state_key LIKE %s",
                    (self.session_key, f"{prefix}%")
                )
                count = cur.rowcount
                self.conn.commit()
                logger.info(f"Cleared {count} keys with prefix {prefix}")
                return count
        except Exception as e:
            logger.error(f"Error clearing prefix {prefix}: {e}")
            self.conn.rollback()
            return 0
    
    # === Extended methods for session management ===
    
    def get_user_sessions(self, limit: int = 10) -> List[dict]:
        """
        Get recent sessions for the current user that have tables in the queue.
        
        Used for the history panel to show previous sessions that can be restored.
        Only returns sessions with more than one table in the queue.
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            List of session summaries with metadata
        """
        try:
            with self.conn.cursor() as cur:
                # First, get sessions that have table_queue with more than one entry
                cur.execute(f"""
                    SELECT DISTINCT session_key
                    FROM {self.full_table}
                    WHERE user_email = %s
                      AND state_key LIKE %s
                      AND jsonb_typeof(value) = 'array'
                      AND jsonb_array_length(value) > 1
                    ORDER BY session_key DESC
                    LIMIT %s
                """, (self.user_email, '%:table_queue', limit))
                
                session_keys = [row[0] for row in cur.fetchall()]
                
                if not session_keys:
                    return []
                
                # Now get details for each session
                sessions = []
                for session_key in session_keys:
                    # Get timestamps
                    cur.execute(f"""
                        SELECT 
                            MIN(created_at) as started_at,
                            MAX(updated_at) as last_activity
                        FROM {self.full_table}
                        WHERE session_key = %s
                    """, (session_key,))
                    time_row = cur.fetchone()
                    
                    # Get tables count from queue
                    cur.execute(f"""
                        SELECT jsonb_array_length(value)
                        FROM {self.full_table}
                        WHERE session_key = %s AND state_key LIKE %s
                        LIMIT 1
                    """, (session_key, '%:table_queue'))
                    count_row = cur.fetchone()
                    
                    # Get workflow step
                    cur.execute(f"""
                        SELECT value::text
                        FROM {self.full_table}
                        WHERE session_key = %s AND state_key LIKE %s
                        LIMIT 1
                    """, (session_key, '%:workflow_step'))
                    workflow_row = cur.fetchone()
                    
                    sessions.append({
                        'session_key': session_key,
                        'started_at': time_row[0].isoformat() if time_row and time_row[0] else None,
                        'last_activity': time_row[1].isoformat() if time_row and time_row[1] else None,
                        'tables_count': count_row[0] if count_row else 0,
                        'workflow_step': workflow_row[0].strip('"') if workflow_row and workflow_row[0] else 'browse'
                    })
                
                # Sort by last_activity descending
                sessions.sort(key=lambda x: x['last_activity'] or '', reverse=True)
                
                # Deduplicate: keep only the latest session for each (tables_count, workflow_step)
                # This reduces clutter when multiple sessions have identical state
                seen_signatures = set()
                unique_sessions = []
                for session in sessions:
                    sig = (session['tables_count'], session['workflow_step'])
                    if sig not in seen_signatures:
                        seen_signatures.add(sig)
                        unique_sessions.append(session)
                
                if len(unique_sessions) < len(sessions):
                    logger.info(f"Deduplicated sessions: {len(sessions)} -> {len(unique_sessions)}")
                
                return unique_sessions
                
        except Exception as e:
            logger.error(f"Error getting user sessions: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def delete_session(self, session_key: str) -> int:
        """
        Delete all state for a specific session.
        
        Args:
            session_key: Session key to delete
            
        Returns:
            Number of state items deleted
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM {self.full_table} WHERE session_key = %s",
                    (session_key,)
                )
                count = cur.rowcount
                self.conn.commit()
                logger.info(f"Deleted session {session_key[:16]}... ({count} items)")
                return count
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            self.conn.rollback()
            return 0
