"""
Session context for user identification and session tracking.

Uses HTTP headers forwarded by Databricks Apps reverse proxy:
- X-Forwarded-Email: User email from IdP
- X-Forwarded-User: User identifier from IdP  
- X-Forwarded-Preferred-Username: Username from IdP
- X-Real-Ip: Client IP address
- X-Request-Id: Request UUID

See: https://docs.databricks.com/aws/en/dev-tools/databricks-apps/http-headers
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict
import hashlib
import streamlit as st


@dataclass
class SessionContext:
    """User session context with identity and timing from Databricks Apps headers."""
    user_email: str
    session_start: datetime
    user_id: Optional[str] = None  # X-Forwarded-User
    username: Optional[str] = None  # X-Forwarded-Preferred-Username
    client_ip: Optional[str] = None  # X-Real-Ip
    
    @property
    def session_key(self) -> str:
        """Unique key combining user email and session start time.
        
        Format: {email_hash}_{timestamp}
        This key uniquely identifies a user's session for database storage.
        """
        # Use hash of email for privacy in logs/keys
        email_hash = hashlib.sha256(self.user_email.encode()).hexdigest()[:12]
        timestamp = self.session_start.strftime("%Y%m%d_%H%M%S")
        return f"{email_hash}_{timestamp}"
    
    @property  
    def display_name(self) -> str:
        """User-friendly display name.
        
        Priority: username > email prefix > 'anonymous'
        """
        if self.username:
            return self.username
        if self.user_email and "@" in self.user_email:
            return self.user_email.split("@")[0]
        return "anonymous"
    
    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated (not local/anonymous)."""
        return self.user_email != "anonymous@local"
    
    def to_dict(self) -> dict:
        """Serialize for storage/logging."""
        return {
            "user_email": self.user_email,
            "user_id": self.user_id,
            "username": self.username,
            "display_name": self.display_name,
            "client_ip": self.client_ip,
            "session_start": self.session_start.isoformat(),
            "session_key": self.session_key,
            "is_authenticated": self.is_authenticated
        }


def _get_header(headers: Dict, name: str) -> Optional[str]:
    """Get header value, trying both cases."""
    return headers.get(name) or headers.get(name.lower())


def get_databricks_headers() -> Dict[str, Optional[str]]:
    """
    Get all Databricks Apps forwarded headers.
    
    Available headers (per Databricks docs):
    - X-Forwarded-Host: Original host/domain
    - X-Forwarded-Preferred-Username: Username from IdP
    - X-Forwarded-User: User identifier from IdP
    - X-Forwarded-Email: User email from IdP
    - X-Real-Ip: Client IP address
    - X-Request-Id: Request UUID
    
    Returns dict with all headers (None if not available).
    """
    result = {
        "host": None,
        "username": None,
        "user_id": None,
        "email": None,
        "client_ip": None,
        "request_id": None
    }
    
    # Try to get from Streamlit headers (available in recent versions)
    try:
        headers = st.context.headers
        result["host"] = _get_header(headers, "X-Forwarded-Host")
        result["username"] = _get_header(headers, "X-Forwarded-Preferred-Username")
        result["user_id"] = _get_header(headers, "X-Forwarded-User")
        result["email"] = _get_header(headers, "X-Forwarded-Email")
        result["client_ip"] = _get_header(headers, "X-Real-Ip")
        result["request_id"] = _get_header(headers, "X-Request-Id")
        return result
    except AttributeError:
        pass
    
    # Fallback: Try experimental get_script_run_ctx
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx()
        if ctx and hasattr(ctx, 'request'):
            headers = ctx.request.headers
            result["host"] = _get_header(headers, "X-Forwarded-Host")
            result["username"] = _get_header(headers, "X-Forwarded-Preferred-Username")
            result["user_id"] = _get_header(headers, "X-Forwarded-User")
            result["email"] = _get_header(headers, "X-Forwarded-Email")
            result["client_ip"] = _get_header(headers, "X-Real-Ip")
            result["request_id"] = _get_header(headers, "X-Request-Id")
    except Exception:
        pass
    
    return result


def get_user_email() -> str:
    """
    Get user email from X-Forwarded-Email header.
    
    Falls back to 'anonymous@local' for local development.
    """
    headers = get_databricks_headers()
    return headers.get("email") or "anonymous@local"


def get_session_context() -> SessionContext:
    """
    Get or create session context for current user.
    
    Captures all available Databricks Apps headers on first call.
    Session start time is captured once per Streamlit session.
    """
    # Check if we already have a session context
    if "_session_context" not in st.session_state:
        headers = get_databricks_headers()
        session_start = datetime.now()
        
        st.session_state._session_context = SessionContext(
            user_email=headers.get("email") or "anonymous@local",
            session_start=session_start,
            user_id=headers.get("user_id"),
            username=headers.get("username"),
            client_ip=headers.get("client_ip")
        )
    
    return st.session_state._session_context
