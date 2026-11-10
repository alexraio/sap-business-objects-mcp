"""
Unit tests for Local Desktop Client Bridge (client_bridge.py).
Tests URL endpoint normalization, desktop Keyring credential header resolution, and argument parsing.
"""

from unittest.mock import MagicMock, patch

import anyio
import pytest
from mcp.shared.message import SessionMessage
from mcp.types import JSONRPCError, JSONRPCMessage, JSONRPCRequest
from pydantic import SecretStr

from core.auth.models import AuthCredentials
from deploy.client_bridge import (
    _pipe_client_to_remote,
    format_endpoint_url,
    parse_args,
    resolve_desktop_headers,
)


class TestClientBridge:
    def test_format_endpoint_url_streamable_http(self):
        assert format_endpoint_url("http://server:8000", "streamable-http") == "http://server:8000/mcp"
        assert format_endpoint_url("http://server:8000/", "streamable-http") == "http://server:8000/mcp"
        assert format_endpoint_url("http://server:8000/mcp", "streamable-http") == "http://server:8000/mcp"

    def test_format_endpoint_url_sse(self):
        assert format_endpoint_url("http://server:8000", "sse") == "http://server:8000/sse"
        assert format_endpoint_url("http://server:8000/", "sse") == "http://server:8000/sse"
        assert format_endpoint_url("http://server:8000/sse", "sse") == "http://server:8000/sse"

    def test_resolve_desktop_headers_explicit(self):
        headers = resolve_desktop_headers(username="test_user", password="test_password")
        assert headers["X-SAP-Username"] == "test_user"
        assert headers["X-SAP-Password"] == "test_password"

    def test_resolve_desktop_headers_from_keyring(self):
        mock_creds = AuthCredentials(username="keyring_admin", password=SecretStr("keyring_pass"))
        with patch("deploy.client_bridge.ChainedCredentialProvider") as mock_provider_cls:
            mock_inst = MagicMock()
            mock_inst.get_credentials.return_value = mock_creds
            mock_provider_cls.return_value = mock_inst

            headers = resolve_desktop_headers()
            assert headers["X-SAP-Username"] == "keyring_admin"
            assert headers["X-SAP-Password"] == "keyring_pass"

    def test_resolve_desktop_headers_missing(self, monkeypatch):
        monkeypatch.delenv("SAP_BO_USERNAME", raising=False)
        monkeypatch.delenv("SAP_BO_PASSWORD", raising=False)
        with patch("deploy.client_bridge.ChainedCredentialProvider") as mock_provider_cls:
            mock_inst = MagicMock()
            mock_inst.get_credentials.return_value = None
            mock_provider_cls.return_value = mock_inst

            headers = resolve_desktop_headers()
            assert headers == {}

    def test_parse_args_defaults_and_custom(self):
        args = parse_args(["--remote-url", "http://bo-linux:8000", "--transport", "sse", "--timeout", "15.0"])
        assert args.remote_url == "http://bo-linux:8000"
        assert args.transport == "sse"
        assert args.timeout == 15.0

    @pytest.mark.anyio
    async def test_pipe_client_intercepts_server_discover(self):
        source_send, source_recv = anyio.create_memory_object_stream(10)
        dest_send, dest_recv = anyio.create_memory_object_stream(10)
        local_send, local_recv = anyio.create_memory_object_stream(10)

        msg = SessionMessage(
            message=JSONRPCMessage(
                root=JSONRPCRequest(
                    jsonrpc="2.0",
                    id=101,
                    method="server/discover",
                )
            )
        )
        await source_send.send(msg)
        await source_send.aclose()

        with anyio.CancelScope() as scope:
            await _pipe_client_to_remote(
                source_recv, dest_send, local_send, scope, get_session_id=lambda: "session-123"
            )

        resp = await local_recv.receive()
        assert isinstance(resp.message.root, JSONRPCError)
        assert resp.message.root.id == 101
        assert resp.message.root.error.code == -32602
        assert "server/discover" in resp.message.root.error.message
        assert dest_recv.statistics().current_buffer_used == 0

    @pytest.mark.anyio
    async def test_pipe_client_intercepts_uninitialized_call(self):
        source_send, source_recv = anyio.create_memory_object_stream(10)
        dest_send, dest_recv = anyio.create_memory_object_stream(10)
        local_send, local_recv = anyio.create_memory_object_stream(10)

        msg = SessionMessage(
            message=JSONRPCMessage(
                root=JSONRPCRequest(
                    jsonrpc="2.0",
                    id=102,
                    method="tools/list",
                )
            )
        )
        await source_send.send(msg)
        await source_send.aclose()

        with anyio.CancelScope() as scope:
            await _pipe_client_to_remote(source_recv, dest_send, local_send, scope, get_session_id=lambda: None)

        resp = await local_recv.receive()
        assert isinstance(resp.message.root, JSONRPCError)
        assert resp.message.root.id == 102
        assert resp.message.root.error.code == -32602
        assert "tools/list" in resp.message.root.error.message
        assert dest_recv.statistics().current_buffer_used == 0

    @pytest.mark.anyio
    async def test_pipe_client_forwards_initialize_and_initialized_calls(self):
        source_send, source_recv = anyio.create_memory_object_stream(10)
        dest_send, dest_recv = anyio.create_memory_object_stream(10)
        local_send, _ = anyio.create_memory_object_stream(10)

        init_msg = SessionMessage(
            message=JSONRPCMessage(
                root=JSONRPCRequest(
                    jsonrpc="2.0",
                    id=103,
                    method="initialize",
                )
            )
        )
        await source_send.send(init_msg)
        await source_send.aclose()

        with anyio.CancelScope() as scope:
            await _pipe_client_to_remote(source_recv, dest_send, local_send, scope, get_session_id=lambda: None)

        fwd = await dest_recv.receive()
        assert fwd.message.root.method == "initialize"
        assert fwd.message.root.id == 103
