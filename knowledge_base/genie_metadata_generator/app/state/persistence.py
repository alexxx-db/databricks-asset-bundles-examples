"""
Persistence service for saving and restoring Genify sessions.
Handles all interactions with the relational database schema.
"""
import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from .schema import ensure_genify_schema_exists

logger = logging.getLogger(__name__)


class PersistenceService:
    """
    Service for persisting and restoring Genify sessions.
    
    Uses proper relational database schema instead of generic key-value storage.
    All operations are explicit - no auto-save.
    """
    
    def __init__(self, connection, user_email: str):
        """
        Initialize persistence service.
        
        Args:
            connection: psycopg2 connection object
            user_email: Current user's email
        """
        self.conn = connection
        self.user_email = user_email
        
        # Ensure schema exists on initialization
        ensure_genify_schema_exists(connection)
        logger.info(f"PersistenceService initialized for user: {user_email}")
    
    # === Session Management ===
    
    def save_session(
        self,
        session_key: str,
        state_manager,
        session_name: Optional[str] = None,
        add_to_library: bool = False,
        library_service: Optional['LibraryService'] = None
    ) -> int:
        """
        Save complete session state including in-progress interviews.
        
        Args:
            session_key: Unique session identifier
            state_manager: StateManager instance with current state
            session_name: Optional user-provided session name
            add_to_library: If True, save both table and Genie YAMLs to library
            library_service: Optional LibraryService for saving to library
        
        Returns:
            session_id from genify.sessions table
        """
        try:
            with self.conn.cursor() as cur:
                # 1. Insert or update session metadata
                workflow_step = state_manager.get_workflow_step()
                
                cur.execute("""
                    INSERT INTO genify.sessions 
                        (session_key, user_email, session_name, workflow_step, last_saved_at, last_activity_at)
                    VALUES (%s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (session_key) 
                    DO UPDATE SET 
                        session_name = EXCLUDED.session_name,
                        workflow_step = EXCLUDED.workflow_step,
                        last_saved_at = NOW(),
                        last_activity_at = NOW()
                    RETURNING id
                """, (session_key, self.user_email, session_name, workflow_step))
                
                session_id = cur.fetchone()[0]
                logger.info(f"Saved session metadata: session_id={session_id}")
                
                # 2. Save completed tables
                completed_tables = state_manager.get_completed_tables()
                for table_data in completed_tables:
                    self._save_completed_table(cur, session_id, table_data)
                
                logger.info(f"Saved {len(completed_tables)} completed tables")
                
                # 3. Save session snapshot (queue + interview states)
                self._save_session_snapshot(cur, session_id, session_key, state_manager)
                
                # 4. Save Genie YAML if complete
                genie_yaml = state_manager.get_tier2_yaml()
                if genie_yaml:
                    self._save_genie_space(cur, session_id, genie_yaml, len(completed_tables))
                    logger.info("Saved Genie space YAML")
                
                # 5. Save to YAML library using LibraryService
                if add_to_library and completed_tables:
                    if library_service and library_service.is_available():
                        skip_genie = state_manager.get_skip_genie()
                        saved_count = library_service.save_yamls(
                            completed_tables=completed_tables,
                            genie_yaml=genie_yaml,
                            skip_genie=skip_genie,
                            tags=None  # Tags not available in save_session context
                        )
                        logger.info(f"Saved {saved_count} YAMLs to library via LibraryService")
                    else:
                        logger.warning("Cannot save to library: LibraryService unavailable")
                
                self.conn.commit()
                logger.info(f"✓ Session saved successfully: {session_key}")
                return session_id
                
        except Exception as e:
            logger.error(f"Error saving session: {e}", exc_info=True)
            self.conn.rollback()
            raise
    
    def _save_completed_table(self, cur, session_id: int, table_data: Dict):
        """Save a completed table to genify.saved_tables."""
        cur.execute("""
            INSERT INTO genify.saved_tables 
                (session_id, user_email, catalog, schema, table_name, 
                 table_metadata, table_comment_yaml, profile_summary)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            ON CONFLICT (session_id, catalog, schema, table_name)
            DO UPDATE SET 
                table_metadata = EXCLUDED.table_metadata,
                table_comment_yaml = EXCLUDED.table_comment_yaml,
                profile_summary = EXCLUDED.profile_summary,
                saved_at = NOW()
        """, (
            session_id,
            self.user_email,
            table_data['catalog'],
            table_data['schema'],
            table_data['table'],
            json.dumps(table_data.get('metadata', {})),
            table_data.get('tier1_yaml', ''),
            table_data.get('profile_summary', '')
        ))
    
    def _save_session_snapshot(self, cur, session_id: int, session_key: str, state_manager):
        """Save session snapshot with queue and interview states."""
        table_queue = state_manager.get_table_queue()
        current_index = state_manager.get_current_table_index()
        workflow_step = state_manager.get_workflow_step()
        
        # Serialize interview states if they exist
        table_interview = state_manager.get_table_interview()
        table_interview_state = table_interview.to_dict() if table_interview else None
        
        genie_interview = state_manager.get_genie_interview()
        genie_interview_state = genie_interview.to_dict() if genie_interview else None
        
        cur.execute("""
            INSERT INTO genify.session_snapshots 
                (session_id, user_email, table_queue, current_table_index, 
                 table_interview_state, genie_interview_state, workflow_step)
            VALUES (%s, %s, %s::jsonb, %s, %s::jsonb, %s::jsonb, %s)
            ON CONFLICT (session_id)
            DO UPDATE SET
                table_queue = EXCLUDED.table_queue,
                current_table_index = EXCLUDED.current_table_index,
                table_interview_state = EXCLUDED.table_interview_state,
                genie_interview_state = EXCLUDED.genie_interview_state,
                workflow_step = EXCLUDED.workflow_step,
                saved_at = NOW()
        """, (
            session_id,
            self.user_email,
            json.dumps(table_queue),
            current_index,
            json.dumps(table_interview_state) if table_interview_state else None,
            json.dumps(genie_interview_state) if genie_interview_state else None,
            workflow_step
        ))
    
    def _save_genie_space(self, cur, session_id: int, genie_yaml: str, table_count: int):
        """Save Genie space configuration."""
        cur.execute("""
            INSERT INTO genify.genie_spaces 
                (session_id, user_email, genie_yaml, table_count)
            VALUES (%s, %s, %s, %s)
        """, (session_id, self.user_email, genie_yaml, table_count))
    
    def restore_session(self, session_key: str) -> Optional[Dict]:
        """
        Restore full session state from database.
        
        Args:
            session_key: Session key to restore
        
        Returns:
            Dict with:
                - completed_tables: List[dict]
                - table_queue: List[dict]
                - current_table_index: int
                - table_interview: dict | None
                - genie_interview: dict | None
                - genie_yaml: str | None
                - workflow_step: str
            Or None if session not found
        """
        try:
            with self.conn.cursor() as cur:
                # Get session ID
                cur.execute("""
                    SELECT id FROM genify.sessions 
                    WHERE session_key = %s AND user_email = %s
                """, (session_key, self.user_email))
                
                row = cur.fetchone()
                if not row:
                    logger.warning(f"Session not found: {session_key}")
                    return None
                
                session_id = row[0]
                
                # Get completed tables
                cur.execute("""
                    SELECT catalog, schema, table_name, table_metadata, 
                           table_comment_yaml, profile_summary, saved_at
                    FROM genify.saved_tables
                    WHERE session_id = %s
                    ORDER BY saved_at
                """, (session_id,))
                
                completed_tables = []
                for row in cur.fetchall():
                    completed_tables.append({
                        'catalog': row[0],
                        'schema': row[1],
                        'table': row[2],
                        'metadata': row[3] if row[3] else {},
                        'tier1_yaml': row[4],
                        'profile_summary': row[5],
                        'timestamp': row[6].strftime("%Y-%m-%d %H:%M") if row[6] else 'Unknown'
                    })
                
                # Get session snapshot
                cur.execute("""
                    SELECT table_queue, current_table_index, 
                           table_interview_state, genie_interview_state, workflow_step
                    FROM genify.session_snapshots
                    WHERE session_id = %s
                """, (session_id,))
                
                snapshot = cur.fetchone()
                if not snapshot:
                    logger.warning(f"No snapshot found for session: {session_key}")
                    return None
                
                # Get Genie YAML if exists
                cur.execute("""
                    SELECT genie_yaml FROM genify.genie_spaces
                    WHERE session_id = %s
                    ORDER BY saved_at DESC
                    LIMIT 1
                """, (session_id,))
                
                genie_row = cur.fetchone()
                genie_yaml = genie_row[0] if genie_row else None
                
                result = {
                    'completed_tables': completed_tables,
                    'table_queue': snapshot[0],  # JSONB auto-converted
                    'current_table_index': snapshot[1],
                    'table_interview': snapshot[2],  # JSONB auto-converted
                    'genie_interview': snapshot[3],  # JSONB auto-converted
                    'workflow_step': snapshot[4],
                    'genie_yaml': genie_yaml
                }
                
                logger.info(f"Restored session: {len(completed_tables)} tables, workflow={snapshot[4]}")
                return result
                
        except Exception as e:
            logger.error(f"Error restoring session: {e}", exc_info=True)
            return None
    
    def list_user_sessions(self, limit: int = 10) -> List[Dict]:
        """
        Get recent saved sessions for current user.
        
        Args:
            limit: Maximum number of sessions to return
        
        Returns:
            List of session summaries with metadata
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        s.id,
                        s.session_key,
                        s.session_name,
                        s.workflow_step,
                        s.started_at,
                        s.last_saved_at,
                        COUNT(DISTINCT st.id) as table_count
                    FROM genify.sessions s
                    LEFT JOIN genify.saved_tables st ON s.id = st.session_id
                    WHERE s.user_email = %s
                    GROUP BY s.id, s.session_key, s.session_name, s.workflow_step, 
                             s.started_at, s.last_saved_at
                    ORDER BY s.last_saved_at DESC NULLS LAST
                    LIMIT %s
                """, (self.user_email, limit))
                
                sessions = []
                for row in cur.fetchall():
                    sessions.append({
                        'id': row[0],
                        'session_key': row[1],
                        'name': row[2],
                        'workflow_step': row[3],
                        'started_at': row[4].isoformat() if row[4] else None,
                        'saved_at': row[5].isoformat() if row[5] else None,
                        'table_count': row[6]
                    })
                
                logger.info(f"Found {len(sessions)} saved sessions for user")
                return sessions
                
        except Exception as e:
            logger.error(f"Error listing sessions: {e}", exc_info=True)
            return []
    
    def rename_session(self, session_key: str, new_name: str) -> bool:
        """
        Rename a session.
        
        Args:
            session_key: Session key to rename
            new_name: New session name
            
        Returns:
            True if renamed, False otherwise
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE genify.sessions 
                    SET session_name = %s
                    WHERE session_key = %s AND user_email = %s
                """, (new_name, session_key, self.user_email))
                
                updated = cur.rowcount > 0
                self.conn.commit()
                
                if updated:
                    logger.info(f"Renamed session {session_key} to '{new_name}'")
                else:
                    logger.warning(f"Session not found for rename: {session_key}")
                
                return updated
                
        except Exception as e:
            logger.error(f"Error renaming session: {e}", exc_info=True)
            self.conn.rollback()
            return False
    
    def delete_session(self, session_key: str) -> bool:
        """
        Delete session and all related data.
        
        Args:
            session_key: Session key to delete
        
        Returns:
            True if deleted, False otherwise
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM genify.sessions 
                    WHERE session_key = %s AND user_email = %s
                """, (session_key, self.user_email))
                
                deleted = cur.rowcount > 0
                self.conn.commit()
                
                if deleted:
                    logger.info(f"Deleted session: {session_key}")
                else:
                    logger.warning(f"Session not found for deletion: {session_key}")
                
                return deleted
                
        except Exception as e:
            logger.error(f"Error deleting session: {e}", exc_info=True)
            self.conn.rollback()
            return False
    
    # === YAML Library ===
    
    def save_to_library(
        self,
        catalog: str,
        schema: str,
        table: str,
        yaml_content: str,
        yaml_type: str,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None
    ) -> int:
        """
        Save YAML to library for reuse.
        
        Args:
            catalog: Catalog name
            schema: Schema name
            table: Table name
            yaml_content: YAML content
            yaml_type: 'table_comment' or 'genie_space'
            metadata: Optional metadata dict
            tags: Optional list of tags
        
        Returns:
            ID of saved YAML
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO genify.yaml_library 
                        (user_email, catalog, schema, table_name, yaml_type, 
                         yaml_content, metadata, tags)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                    ON CONFLICT (user_email, catalog, schema, table_name, yaml_type)
                    DO UPDATE SET
                        yaml_content = EXCLUDED.yaml_content,
                        metadata = EXCLUDED.metadata,
                        tags = EXCLUDED.tags,
                        updated_at = NOW()
                    RETURNING id
                """, (
                    self.user_email,
                    catalog,
                    schema,
                    table,
                    yaml_type,
                    yaml_content,
                    json.dumps(metadata) if metadata else None,
                    tags
                ))
                
                yaml_id = cur.fetchone()[0]
                self.conn.commit()
                logger.info(f"Saved YAML to library: {catalog}.{schema}.{table} (id={yaml_id})")
                return yaml_id
                
        except Exception as e:
            logger.error(f"Error saving to library: {e}", exc_info=True)
            self.conn.rollback()
            raise
    
    def get_from_library(
        self,
        yaml_type: Optional[str] = None,
        catalog: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get YAMLs from library with optional filters.
        
        Args:
            yaml_type: Optional filter by type
            catalog: Optional filter by catalog
            limit: Maximum number to return
        
        Returns:
            List of YAML library items
        """
        try:
            with self.conn.cursor() as cur:
                # Build query with optional filters
                query = """
                    SELECT id, catalog, schema, table_name, yaml_type, 
                           yaml_content, metadata, tags, created_at, updated_at
                    FROM genify.yaml_library
                    WHERE user_email = %s
                """
                params = [self.user_email]
                
                if yaml_type:
                    query += " AND yaml_type = %s"
                    params.append(yaml_type)
                
                if catalog:
                    query += " AND catalog = %s"
                    params.append(catalog)
                
                query += " ORDER BY updated_at DESC LIMIT %s"
                params.append(limit)
                
                cur.execute(query, params)
                
                items = []
                for row in cur.fetchall():
                    items.append({
                        'id': row[0],
                        'catalog': row[1],
                        'schema': row[2],
                        'table_name': row[3],
                        'yaml_type': row[4],
                        'yaml_content': row[5],
                        'metadata': row[6] if row[6] else {},
                        'tags': row[7] if row[7] else [],
                        'created_at': row[8].isoformat() if row[8] else None,
                        'updated_at': row[9].isoformat() if row[9] else None
                    })
                
                logger.info(f"Retrieved {len(items)} YAMLs from library")
                return items
                
        except Exception as e:
            logger.error(f"Error getting from library: {e}", exc_info=True)
            return []
    
    def search_library(self, query: str, limit: int = 50) -> List[Dict]:
        """
        Search YAML library by text query.
        
        Args:
            query: Search query
            limit: Maximum number to return
        
        Returns:
            List of matching YAML library items
        """
        try:
            with self.conn.cursor() as cur:
                search_pattern = f"%{query}%"
                
                cur.execute("""
                    SELECT id, catalog, schema, table_name, yaml_type, 
                           yaml_content, metadata, tags, created_at, updated_at
                    FROM genify.yaml_library
                    WHERE user_email = %s
                      AND (
                          table_name ILIKE %s
                          OR catalog ILIKE %s
                          OR schema ILIKE %s
                          OR %s = ANY(tags)
                      )
                    ORDER BY updated_at DESC
                    LIMIT %s
                """, (self.user_email, search_pattern, search_pattern, search_pattern, query, limit))
                
                items = []
                for row in cur.fetchall():
                    items.append({
                        'id': row[0],
                        'catalog': row[1],
                        'schema': row[2],
                        'table_name': row[3],
                        'yaml_type': row[4],
                        'yaml_content': row[5],
                        'metadata': row[6] if row[6] else {},
                        'tags': row[7] if row[7] else [],
                        'created_at': row[8].isoformat() if row[8] else None,
                        'updated_at': row[9].isoformat() if row[9] else None
                    })
                
                logger.info(f"Found {len(items)} YAMLs matching query: {query}")
                return items
                
        except Exception as e:
            logger.error(f"Error searching library: {e}", exc_info=True)
            return []
    
    def update_library_entry(self, library_id: int, yaml_content: str) -> bool:
        """
        Update YAML content for a library entry.
        
        Args:
            library_id: ID of the library entry to update
            yaml_content: New YAML content
        
        Returns:
            True if updated successfully
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE genify.yaml_library
                    SET yaml_content = %s, updated_at = NOW()
                    WHERE id = %s AND user_email = %s
                """, (yaml_content, library_id, self.user_email))
                
                updated = cur.rowcount > 0
                self.conn.commit()
                
                if updated:
                    logger.info(f"Updated library entry {library_id}")
                else:
                    logger.warning(f"Library entry not found: {library_id}")
                
                return updated
                
        except Exception as e:
            logger.error(f"Error updating library entry: {e}", exc_info=True)
            self.conn.rollback()
            return False
    
    def delete_from_library(self, yaml_id: int) -> bool:
        """
        Delete YAML from library.
        
        Args:
            yaml_id: ID of YAML to delete
        
        Returns:
            True if deleted, False otherwise
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM genify.yaml_library 
                    WHERE id = %s AND user_email = %s
                """, (yaml_id, self.user_email))
                
                deleted = cur.rowcount > 0
                self.conn.commit()
                
                if deleted:
                    logger.info(f"Deleted YAML from library: id={yaml_id}")
                else:
                    logger.warning(f"YAML not found for deletion: id={yaml_id}")
                
                return deleted
                
        except Exception as e:
            logger.error(f"Error deleting from library: {e}", exc_info=True)
            self.conn.rollback()
            return False
