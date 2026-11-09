"""
Unit tests for Local Desktop Client Bridge (client_bridge.py).
Tests URL endpoint normalization, desktop Keyring credential header resolution, and argument parsing.
"""

from unittest.mock import MagicMock, patch

from pydantic import SecretStr

from core.auth.models import AuthCredentials
from deploy.client_bridge import format_endpoint_url, parse_args, resolve_desktop_headers


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
