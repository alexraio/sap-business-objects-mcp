"""
Session Management and Multi-User Isolation for SAP BusinessObjects MCP.
Maintains isolated BOESDKParser and BOEClient instances per connected client/session,
preserving individual user rights, data security profiles, and logon tokens.
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from sdk_parser_new import BOESDKParser

from .auth.models import AuthCredentials
from .auth.providers import ChainedCredentialProvider, CredentialProvider

logger = logging.getLogger("BOESessionManager")


@dataclass
class UserSession:
    """
    Encapsulates an isolated SAP BusinessObjects user session.
    Guarantees that individual SAP logon tokens and permissions never leak across sessions.
    """

    session_id: str
    parser: BOESDKParser
    credentials: Optional[AuthCredentials] = None
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
        """
        self.touch()
        user = username or (self.credentials.username if self.credentials else None)
        pwd = password or (self.credentials.get_password() if self.credentials else None)
        auth = auth_type or (self.credentials.auth_type if self.credentials else "secEnterprise")

        if not user or not pwd:
            raise ValueError("Missing credentials: no username/password provided and none found in .env or OS Keyring.")

        token = self.parser.client.set_logon_token(username=user, password=pwd, auth=auth)
        return token

    def logoff(self) -> bool:
        """Logs off and invalidates active session token."""
        self.touch()
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
    ):
        self._sessions: Dict[str, UserSession] = {}
        self._lock = threading.Lock()
        self.credential_provider = credential_provider or ChainedCredentialProvider()
        self.session_ttl_seconds = session_ttl_seconds

    def get_or_create_session(
        self,
        session_id: str = "default",
        credentials: Optional[AuthCredentials] = None,
    ) -> UserSession:
        """
        Retrieves an existing UserSession or instantiates a new one if not present.
        Thread-safe.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is not None:
                session.touch()
                return session

            # Resolve credentials for the new session
            creds = credentials or self.credential_provider.get_credentials()

            # Initialize isolated parser
            api_url = creds.api_url if creds and creds.api_url else None
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
