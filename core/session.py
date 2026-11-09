"""
Session Management and Multi-User Isolation for SAP BusinessObjects MCP.
Maintains isolated BOESDKParser and BOEClient instances per connected client/session,
preserving individual user rights, data security profiles, logon tokens, and RBAC admin status.
"""

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from sdk_parser_new import BOESDKParser

from .auth.models import AuthCredentials
from .auth.providers import ChainedCredentialProvider, CredentialProvider
from .exceptions import BOEPermissionError

logger = logging.getLogger("BOESessionManager")


@dataclass
class UserSession:
    """
    Encapsulates an isolated SAP BusinessObjects user session.
    Guarantees that individual SAP logon tokens, permissions, and RBAC roles never leak across sessions.
    """

    session_id: str
    parser: BOESDKParser
    credentials: Optional[AuthCredentials] = None
    authenticated_user: Optional[str] = None
    is_admin: Optional[bool] = None
    created_at: float = field(default_factory=time.time)
    last_accessed_at: float = field(default_factory=time.time)

    def touch(self) -> None:
        """Updates last accessed timestamp."""
        self.last_accessed_at = time.time()

    @property
    def is_authenticated(self) -> bool:
        """Checks if session holds an active SAP BO logon token."""
        return bool(self.parser.logon_token)

    def authenticate(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        auth_type: str = "secEnterprise",
    ) -> str:
        """
        Authenticates the session against SAP BusinessObjects.
        Uses explicit username/password if provided, or stored credentials otherwise.
        Also resolves and caches the user's RBAC Administrator status.
        """
        self.touch()
        user = username or (self.credentials.username if self.credentials else None)
        pwd = password or (self.credentials.get_password() if self.credentials else None)
        auth = auth_type or (self.credentials.auth_type if self.credentials else "secEnterprise")

        if not user or not pwd:
            raise ValueError("Missing credentials: no username/password provided and none found in .env or OS Keyring.")

        token = self.parser.client.set_logon_token(username=user, password=pwd, auth=auth)
        self.authenticated_user = user
        self.is_admin = True if user.strip().lower() == "administrator" else None
        return token

    def check_admin_status(self) -> bool:
        """
        Determines and caches whether the current session user belongs to SAP BO Administrators.
        """
        self.touch()
        if self.is_admin is not None:
            return self.is_admin

        user = (
            self.authenticated_user
            or (self.credentials.username if self.credentials else None)
            or os.getenv("SAP_BO_USERNAME")
        )
        if not user:
            return False

        self.is_admin = self.parser.admin.is_user_admin(user)
        return self.is_admin

    def ensure_admin(self) -> None:
        """
        Enforces SAP BusinessObjects Administrator RBAC on restricted tools (LogService and AuditService).
        Raises BOEPermissionError if the current session is not an administrator.
        """
        if not self.check_admin_status():
            user_label = self.authenticated_user or (self.credentials.username if self.credentials else "anonymous")
            raise BOEPermissionError(
                f"Access denied for user '{user_label}' (session '{self.session_id}'): "
                "SAP BusinessObjects Administrator privileges (membership in 'Administrators' group) "
                "are required to inspect local server logs or query the Auditing Database."
            )

    def logoff(self) -> bool:
        """Logs off and invalidates active session token."""
        self.touch()
        self.authenticated_user = None
        self.is_admin = None
        try:
            return self.parser.bo_logoff()
        except Exception as e:
            logger.warning(f"Error logging off session '{self.session_id}': {e}")
            return False


class SessionManager:
    """
    Thread-safe session manager coordinating isolated UserSession instances.
    Provides local default session fallback for stdio MCP clients,
    and distinct isolated sessions for remote/concurrent HTTP/SSE clients.
    """

    def __init__(
        self,
        credential_provider: Optional[CredentialProvider] = None,
        session_ttl_seconds: int = 3600,
        remote_mode: bool = False,
    ):
        self._sessions: Dict[str, UserSession] = {}
        self._lock = threading.Lock()
        self.credential_provider = credential_provider or ChainedCredentialProvider()
        self.session_ttl_seconds = session_ttl_seconds
        self.remote_mode = remote_mode
        self._cleanup_stop_event = threading.Event()
        self._cleanup_thread: Optional[threading.Thread] = None

    def get_or_create_session(
        self,
        session_id: str = "default",
        credentials: Optional[AuthCredentials] = None,
        allow_credential_fallback: Optional[bool] = None,
    ) -> UserSession:
        """
        Retrieves an existing UserSession or instantiates a new one if not present.
        In remote HTTP/SSE mode (remote_mode=True), automatic fallback to server .env/Keyring
        credentials is disabled by default so remote clients cannot inherit server credentials.
        Thread-safe.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is not None:
                session.touch()
                return session

            use_fallback = (not self.remote_mode) if allow_credential_fallback is None else allow_credential_fallback
            creds = credentials or (self.credential_provider.get_credentials() if use_fallback else None)

            # Initialize isolated parser (in remote mode, still respect SAP_BO_REST_API_URL if set)
            api_url = (creds.api_url if creds and creds.api_url else None) or os.getenv("SAP_BO_REST_API_URL")
            parser = BOESDKParser(base_url=api_url) if api_url else BOESDKParser()

            session = UserSession(
                session_id=session_id,
                parser=parser,
                credentials=creds,
            )
            self._sessions[session_id] = session
            logger.info(f"Initialized new isolated UserSession for session_id='{session_id}'")
            return session

    def get_parser(self, session_id: str = "default") -> BOESDKParser:
        """Convenience method returning the BOESDKParser for a given session."""
        session = self.get_or_create_session(session_id)
        return session.parser

    def invalidate_session(self, session_id: str) -> bool:
        """Logs off and terminates a specific session."""
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                return session.logoff()
            return False

    def cleanup_expired_sessions(self) -> int:
        """Cleans up inactive sessions that exceeded TTL."""
        now = time.time()
        expired_ids = []
        with self._lock:
            for s_id, session in list(self._sessions.items()):
                if now - session.last_accessed_at > self.session_ttl_seconds:
                    expired_ids.append(s_id)

            for s_id in expired_ids:
                session = self._sessions.pop(s_id, None)
                if session:
                    session.logoff()

        return len(expired_ids)

    def get_active_sessions_count(self) -> int:
        """Returns total active isolated sessions."""
        with self._lock:
            return len(self._sessions)

    def start_background_cleanup(self, interval_seconds: int = 300) -> None:
        """Starts a background daemon thread that periodically cleans up expired SAP BO sessions."""
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            return

        self._cleanup_stop_event.clear()

        def _worker() -> None:
            while not self._cleanup_stop_event.wait(timeout=interval_seconds):
                try:
                    cleaned = self.cleanup_expired_sessions()
                    if cleaned > 0:
                        logger.info(f"Background session cleanup released {cleaned} expired SAP BO session(s).")
                except Exception as e:
                    logger.warning(f"Error in background session cleanup worker: {e}")

        self._cleanup_thread = threading.Thread(target=_worker, name="BOESessionCleanup", daemon=True)
        self._cleanup_thread.start()

    def stop_background_cleanup(self) -> None:
        """Stops the background session cleanup worker thread."""
        self._cleanup_stop_event.set()
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=2.0)
