"""
Unit tests for SessionManager and isolated UserSession lifecycle.
"""

import time
from unittest.mock import MagicMock

from pydantic import SecretStr

from core.auth.models import AuthCredentials
from core.session import SessionManager


class TestSessionManager:
    def test_get_or_create_session_defaults(self):
        manager = SessionManager()
        session = manager.get_or_create_session("default")

        assert session is not None
        assert session.session_id == "default"
        assert manager.get_active_sessions_count() == 1

        # Second call returns existing session
        same_session = manager.get_or_create_session("default")
        assert same_session is session
        assert manager.get_active_sessions_count() == 1

    def test_session_isolation_multi_user(self):
        """Verifies that distinct session IDs create independent parsers and clients."""
        manager = SessionManager()

        creds_alice = AuthCredentials(username="alice", password=SecretStr("alice_pwd"))
        creds_bob = AuthCredentials(username="bob", password=SecretStr("bob_pwd"))

        session_alice = manager.get_or_create_session("session_alice", credentials=creds_alice)
        session_bob = manager.get_or_create_session("session_bob", credentials=creds_bob)

        assert session_alice is not session_bob
        assert session_alice.parser is not session_bob.parser
        assert session_alice.parser.client is not session_bob.parser.client

        # Simulate authentication on Alice's session
        session_alice.parser.client.logon_token = "ALICE_TOKEN_123"
        session_bob.parser.client.logon_token = "BOB_TOKEN_456"

        assert session_alice.parser.logon_token == "ALICE_TOKEN_123"
        assert session_bob.parser.logon_token == "BOB_TOKEN_456"
        assert session_alice.is_authenticated is True
        assert session_bob.is_authenticated is True

    def test_invalidate_session(self):
        manager = SessionManager()
        session = manager.get_or_create_session("to_remove")
        session.parser.bo_logoff = MagicMock(return_value=True)

        assert manager.get_active_sessions_count() == 1
        success = manager.invalidate_session("to_remove")

        assert success is True
        assert manager.get_active_sessions_count() == 0
        session.parser.bo_logoff.assert_called_once()

    def test_cleanup_expired_sessions(self):
        manager = SessionManager(session_ttl_seconds=1)

        s1 = manager.get_or_create_session("expired_session")
        s2 = manager.get_or_create_session("fresh_session")

        s1.parser.bo_logoff = MagicMock(return_value=True)
        s2.parser.bo_logoff = MagicMock(return_value=True)

        # Force s1 last_accessed_at to 2 seconds ago
        s1.last_accessed_at = time.time() - 2.0
        s2.last_accessed_at = time.time()  # fresh

        expired_count = manager.cleanup_expired_sessions()
        assert expired_count == 1
        assert manager.get_active_sessions_count() == 1
        s1.parser.bo_logoff.assert_called_once()
        s2.parser.bo_logoff.assert_not_called()
