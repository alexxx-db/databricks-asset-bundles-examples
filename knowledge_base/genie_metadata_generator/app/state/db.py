"""
Lakebase database connection management.

Handles PostgreSQL connection for Databricks Apps using Lakebase.
Uses psycopg2 for synchronous connections compatible with Streamlit.

Databricks Apps automatically sets these environment variables when
a database resource is added:
    - PGHOST: PostgreSQL host
    - PGPORT: PostgreSQL port
    - PGDATABASE: Database name
    - PGUSER: Service principal's client ID
    - PGSSLMODE: SSL mode for connection

See: https://docs.databricks.com/aws/en/dev-tools/databricks-apps/lakebase
"""
import os
import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .persistence import PersistenceService

logger = logging.getLogger(__name__)

# Global connection cache
_connection = None


def get_lakebase_connection():
    """
    Get or create a Lakebase PostgreSQL connection.
    
    In Databricks Apps, connection details are provided via standard
    PostgreSQL environment variables (PGHOST, PGPORT, etc.) set automatically
    when you add a database resource.
    
    For local development, you can use LAKEBASE_* variables as fallback.
    
    Returns:
        psycopg2 connection object
        
    Raises:
        ImportError: If psycopg2 is not installed
        Exception: If connection fails
    """
    global _connection
    
    # Return cached connection if still valid
    if _connection is not None:
        try:
            # Test connection is still alive
            with _connection.cursor() as cur:
                cur.execute("SELECT 1")
            return _connection
        except Exception:
            logger.warning("Lakebase connection lost, reconnecting...")
            _connection = None
    
    try:
        import psycopg2
    except ImportError:
        raise ImportError(
            "psycopg2 is required for Lakebase backend. "
            "Install with: pip install psycopg2-binary"
        )
    
    # Get connection parameters from environment
    # Priority: Standard PG* vars (Databricks Apps) > LAKEBASE_* vars (local dev)
    host = os.getenv("PGHOST") or os.getenv("LAKEBASE_HOST")
    port = os.getenv("PGPORT") or os.getenv("LAKEBASE_PORT", "5432")
    database = os.getenv("PGDATABASE") or os.getenv("LAKEBASE_DATABASE", "postgres")
    user = os.getenv("PGUSER") or os.getenv("LAKEBASE_USER")
    sslmode = os.getenv("PGSSLMODE", "require")
    password = os.getenv("LAKEBASE_PASSWORD")  # Only for local dev; Databricks uses OAuth
    
    if not host:
        raise ValueError(
            "PGHOST environment variable not set. "
            "Ensure a database resource is configured in Databricks Apps, "
            "or set LAKEBASE_HOST for local development."
        )
    
    if not password:
        # Get OAuth token via client credentials flow
        password = _get_oauth_token()
    
    if not password:
        raise ValueError(
            "No password or OAuth token available. "
            "Ensure DATABRICKS_HOST, DATABRICKS_CLIENT_ID, and DATABRICKS_CLIENT_SECRET are set. "
            "For local dev, set LAKEBASE_PASSWORD."
        )
    
    logger.info(f"Connecting to Lakebase at {host}:{port}/{database} (user={user}, sslmode={sslmode})")
    
    try:
        _connection = psycopg2.connect(
            host=host,
            port=int(port),
            database=database,
            user=user,
            password=password,
            sslmode=sslmode,
            connect_timeout=10,
        )
        
        # Set connection to autocommit=False for explicit transaction control
        _connection.autocommit = False
        
        # Log successful connection with server info
        with _connection.cursor() as cur:
            cur.execute("SELECT version()")
            row = cur.fetchone()
            version = row[0].split(",")[0] if row else "unknown"
        logger.info(
            "Lakebase connection established successfully to %s:%s/%s (version: %s)",
            host, port, database, version,
        )
        return _connection
        
    except Exception as e:
        logger.error(f"Failed to connect to Lakebase at {host}:{port}/{database}: {e}")
        raise


def _get_oauth_token() -> Optional[str]:
    """
    Get OAuth token for Lakebase authentication using client credentials flow.
    
    Uses environment variables provided by Databricks Apps:
    - DATABRICKS_HOST: Workspace URL
    - DATABRICKS_CLIENT_ID: Service principal client ID
    - DATABRICKS_CLIENT_SECRET: Service principal secret
    
    Returns:
        OAuth access token string, or None if credentials unavailable
    """
    import requests
    
    host = os.getenv("DATABRICKS_HOST")
    client_id = os.getenv("DATABRICKS_CLIENT_ID")
    client_secret = os.getenv("DATABRICKS_CLIENT_SECRET")
    
    # Check all required credentials are present
    if not host:
        logger.warning("DATABRICKS_HOST not set - cannot obtain OAuth token")
        return None
    if not client_id:
        logger.warning("DATABRICKS_CLIENT_ID not set - cannot obtain OAuth token")
        return None
    if not client_secret:
        logger.warning("DATABRICKS_CLIENT_SECRET not set - cannot obtain OAuth token")
        return None
    
    # Ensure host has https:// scheme
    if not host.startswith("https://") and not host.startswith("http://"):
        host = f"https://{host}"
    
    # OAuth2 token endpoint
    token_url = f"{host.rstrip('/')}/oidc/v1/token"
    
    logger.info(f"Requesting OAuth token from {token_url}")
    
    try:
        response = requests.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "all-apis"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        response.raise_for_status()
        
        token_data = response.json()
        access_token = token_data.get("access_token")
        
        if access_token:
            logger.info("Successfully obtained OAuth token via client credentials flow")
            return access_token
        else:
            logger.warning("OAuth response did not contain access_token")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to obtain OAuth token: {e}")
        return None


def get_lakebase_connection_safe():
    """
    Safely get Lakebase connection, returning None if unavailable.
    
    This is a safe wrapper around get_lakebase_connection() that returns None
    instead of raising exceptions, allowing the app to gracefully degrade to
    in-memory session state when Lakebase is unavailable.
    
    Returns:
        Connection object or None if connection fails
    """
    try:
        return get_lakebase_connection()
    except Exception as e:
        logger.warning(f"Lakebase connection unavailable: {e}")
        return None


def close_connection() -> None:
    """Close the Lakebase connection."""
    global _connection
    
    if _connection is not None:
        try:
            _connection.close()
            logger.info("Lakebase connection closed")
        except Exception as e:
            logger.warning(f"Error closing Lakebase connection: {e}")
        finally:
            _connection = None


def get_connection_status() -> dict:
    """
    Get status of the Lakebase connection.
    
    Returns:
        Dict with connection status information
    """
    global _connection
    
    # Check which env vars are set (for diagnostics)
    host = os.getenv("PGHOST") or os.getenv("LAKEBASE_HOST")
    database = os.getenv("PGDATABASE") or os.getenv("LAKEBASE_DATABASE")
    
    if _connection is None:
        return {
            "connected": False,
            "host": host,
            "database": database,
            "error": "No active connection"
        }
    
    try:
        with _connection.cursor() as cur:
            cur.execute("SELECT current_database(), current_user, inet_server_addr()")
            row = cur.fetchone()
            
            return {
                "connected": True,
                "database": row[0],
                "user": row[1],
                "host": str(row[2]) if row[2] else host,
            }
    except Exception as e:
        return {
            "connected": False,
            "host": host,
            "error": str(e)
        }


def get_persistence_service(user_email: str) -> Optional['PersistenceService']:
    """
    Get PersistenceService instance or None if Lakebase unavailable.
    
    This function gracefully handles:
    - Lakebase disabled in config
    - Connection failures
    - Missing dependencies
    
    Returns None instead of raising exceptions, allowing app to run
    with reduced functionality.
    
    Args:
        user_email: Current user's email
    
    Returns:
        PersistenceService instance or None if unavailable
    """
    from config import config
    
    # Check if Lakebase is enabled first
    if not config.lakebase_enabled:
        logger.debug("PersistenceService unavailable: Lakebase disabled")
        return None
    
    # Try to get connection (returns None on failure)
    conn = get_lakebase_connection_safe()
    if not conn:
        logger.debug("PersistenceService unavailable: Connection failed")
        return None
    
    try:
        from state.persistence import PersistenceService
        return PersistenceService(conn, user_email)
    except Exception as e:
        logger.warning(f"Failed to create PersistenceService: {e}")
        return None
