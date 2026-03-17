"""
Database schema initialization for Genify.
Creates proper relational tables in PostgreSQL (Lakebase) for state persistence.
"""
import logging

logger = logging.getLogger(__name__)


def ensure_genify_schema_exists(connection):
    """
    Create all Genify tables on first run. Idempotent.
    
    Creates:
    - genify.sessions: Session metadata
    - genify.saved_tables: Completed table YAMLs
    - genify.genie_spaces: Genie space configurations
    - genify.yaml_library: Reusable YAML library
    - genify.session_snapshots: In-progress interview states
    
    Args:
        connection: psycopg2 connection object
    """
    try:
        with connection.cursor() as cur:
            # Create schema
            cur.execute("CREATE SCHEMA IF NOT EXISTS genify")
            logger.info("Ensured schema 'genify' exists")
            
            # Table 1: sessions
            cur.execute("""
                CREATE TABLE IF NOT EXISTS genify.sessions (
                    id SERIAL PRIMARY KEY,
                    session_key VARCHAR(64) UNIQUE NOT NULL,
                    user_email VARCHAR(255) NOT NULL,
                    session_name VARCHAR(255),
                    workflow_step VARCHAR(50) NOT NULL DEFAULT 'browse',
                    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    last_saved_at TIMESTAMP,
                    last_activity_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user_email 
                ON genify.sessions(user_email)
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_active 
                ON genify.sessions(user_email, is_active)
            """)
            
            logger.info("Ensured table 'genify.sessions' exists")
            
            # Table 2: saved_tables
            cur.execute("""
                CREATE TABLE IF NOT EXISTS genify.saved_tables (
                    id SERIAL PRIMARY KEY,
                    session_id INTEGER REFERENCES genify.sessions(id) ON DELETE CASCADE,
                    user_email VARCHAR(255) NOT NULL,
                    catalog VARCHAR(255) NOT NULL,
                    schema VARCHAR(255) NOT NULL,
                    table_name VARCHAR(255) NOT NULL,
                    table_metadata JSONB,
                    table_comment_yaml TEXT NOT NULL,
                    profile_summary TEXT,
                    saved_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    UNIQUE(session_id, catalog, schema, table_name)
                )
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_saved_tables_user 
                ON genify.saved_tables(user_email)
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_saved_tables_session 
                ON genify.saved_tables(session_id)
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_saved_tables_table 
                ON genify.saved_tables(catalog, schema, table_name)
            """)
            
            logger.info("Ensured table 'genify.saved_tables' exists")
            
            # Table 3: genie_spaces
            cur.execute("""
                CREATE TABLE IF NOT EXISTS genify.genie_spaces (
                    id SERIAL PRIMARY KEY,
                    session_id INTEGER REFERENCES genify.sessions(id) ON DELETE CASCADE,
                    user_email VARCHAR(255) NOT NULL,
                    space_name VARCHAR(255),
                    genie_yaml TEXT NOT NULL,
                    table_count INTEGER NOT NULL,
                    saved_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_genie_spaces_user 
                ON genify.genie_spaces(user_email)
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_genie_spaces_session 
                ON genify.genie_spaces(session_id)
            """)
            
            logger.info("Ensured table 'genify.genie_spaces' exists")
            
            # Table 4: yaml_library
            cur.execute("""
                CREATE TABLE IF NOT EXISTS genify.yaml_library (
                    id SERIAL PRIMARY KEY,
                    user_email VARCHAR(255) NOT NULL,
                    catalog VARCHAR(255) NOT NULL,
                    schema VARCHAR(255) NOT NULL,
                    table_name VARCHAR(255) NOT NULL,
                    yaml_type VARCHAR(50) NOT NULL,
                    yaml_content TEXT NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    tags TEXT[],
                    UNIQUE(user_email, catalog, schema, table_name, yaml_type)
                )
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_yaml_library_user 
                ON genify.yaml_library(user_email)
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_yaml_library_table 
                ON genify.yaml_library(catalog, schema, table_name)
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_yaml_library_type 
                ON genify.yaml_library(yaml_type)
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_yaml_library_tags 
                ON genify.yaml_library USING GIN(tags)
            """)
            
            logger.info("Ensured table 'genify.yaml_library' exists")
            
            # Table 5: session_snapshots
            cur.execute("""
                CREATE TABLE IF NOT EXISTS genify.session_snapshots (
                    id SERIAL PRIMARY KEY,
                    session_id INTEGER REFERENCES genify.sessions(id) ON DELETE CASCADE,
                    user_email VARCHAR(255) NOT NULL,
                    table_queue JSONB NOT NULL,
                    current_table_index INTEGER DEFAULT 0,
                    table_interview_state JSONB,
                    genie_interview_state JSONB,
                    workflow_step VARCHAR(50) NOT NULL,
                    saved_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    UNIQUE(session_id)
                )
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_snapshots_session 
                ON genify.session_snapshots(session_id)
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_snapshots_user 
                ON genify.session_snapshots(user_email)
            """)
            
            logger.info("Ensured table 'genify.session_snapshots' exists")
            
            connection.commit()
            logger.info("✓ Genify schema initialization complete")
            
    except Exception as e:
        logger.error(f"Error creating Genify schema: {e}")
        connection.rollback()
        raise
