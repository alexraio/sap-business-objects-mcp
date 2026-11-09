"""Tests for HTTPS support: server TLS config, bridge TLS verification, dev cert generator."""

import importlib.util
import socket
import ssl
import threading
import time
from pathlib import Path

import anyio
import httpx
import pytest
import uvicorn
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

import server
from deploy import client_bridge

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_cert_generator():
    spec = importlib.util.spec_from_file_location("generate_dev_cert", PROJECT_ROOT / "deploy" / "generate_dev_cert.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def dev_cert(tmp_path_factory):
    out = tmp_path_factory.mktemp("certs")
    cert, key = out / "dev-cert.pem", out / "dev-key.pem"
    _load_cert_generator().generate_self_signed_cert(["localhost"], cert, key, days=1)
    return cert, key


class TestServerSSLConfig:
    def test_no_tls_returns_empty(self):
        assert server.build_ssl_config(None, None) == {}

    def test_only_one_of_cert_or_key_is_rejected(self, dev_cert):
        cert, key = dev_cert
        with pytest.raises(ValueError, match="both"):
            server.build_ssl_config(str(cert), None)
        with pytest.raises(ValueError, match="both"):
            server.build_ssl_config(None, str(key))

    def test_missing_files_are_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="not found"):
            server.build_ssl_config(str(tmp_path / "a.pem"), str(tmp_path / "b.pem"))

    def test_valid_config(self, dev_cert):
        cert, key = dev_cert
        cfg = server.build_ssl_config(str(cert), str(key), "secret")
        assert cfg == {"ssl_certfile": str(cert), "ssl_keyfile": str(key), "ssl_keyfile_password": "secret"}

    def test_parse_args_reads_ssl_options(self):
        args = server.parse_server_args(["--ssl-certfile", "c.pem", "--ssl-keyfile", "k.pem"])
        assert args.ssl_certfile == "c.pem" and args.ssl_keyfile == "k.pem"


class TestBridgeTLSOptions:
    def test_resolve_tls_verify(self, dev_cert):
        cert, _ = dev_cert
        assert client_bridge.resolve_tls_verify() is True
        assert client_bridge.resolve_tls_verify(insecure=True) is False
        assert isinstance(client_bridge.resolve_tls_verify(str(cert)), ssl.SSLContext)
        with pytest.raises(FileNotFoundError):
            client_bridge.resolve_tls_verify("/nonexistent/ca.pem")

    def test_plain_http_warning_only_for_remote_hosts_with_credentials(self, caplog):
        with caplog.at_level("WARNING", logger="BOEClientBridge"):
            client_bridge.warn_if_insecure_transport("http://localhost:8000", True)
            client_bridge.warn_if_insecure_transport("https://bo-host:8443", True)
            client_bridge.warn_if_insecure_transport("http://bo-host:8000", False)
            assert not caplog.records
            client_bridge.warn_if_insecure_transport("http://bo-host:8000", True)
            assert "plain HTTP" in caplog.text

    def test_parse_args_reads_tls_options(self):
        args = client_bridge.parse_args(["--remote-url", "https://h:8443", "--ca-file", "ca.pem", "--insecure"])
        assert args.ca_file == "ca.pem" and args.insecure is True


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _loopback_available() -> bool:
    try:
        with socket.socket() as listener, socket.socket() as client:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            client.connect(listener.getsockname())
        return True
    except OSError:
        return False


@pytest.fixture
def https_server(dev_cert):
    if not _loopback_available():
        pytest.skip("Loopback TCP connections are not permitted in this environment")
    cert, key = dev_cert
    port = _free_port()

    async def ping(_request):
        return PlainTextResponse("pong")

    app = Starlette(routes=[Route("/ping", ping)])
    config = uvicorn.Config(
        app, host="127.0.0.1", port=port, log_level="error", **server.build_ssl_config(str(cert), str(key))
    )
    uv_server = uvicorn.Server(config)
    thread = threading.Thread(target=uv_server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if uv_server.started:
            break
        time.sleep(0.05)
    assert uv_server.started
    yield f"https://localhost:{port}/ping"
    uv_server.should_exit = True
    thread.join(timeout=5)


class TestHTTPSEndToEnd:
    @staticmethod
    def _get(url, verify):
        async def run():
            async with client_bridge.make_httpx_client_factory(verify)() as client:
                return await client.get(url)

        return anyio.run(run)

    def test_trusted_ca_file_succeeds(self, https_server, dev_cert):
        resp = self._get(https_server, client_bridge.resolve_tls_verify(str(dev_cert[0])))
        assert resp.status_code == 200 and resp.text == "pong"

    def test_insecure_succeeds(self, https_server):
        assert self._get(https_server, False).text == "pong"

    def test_untrusted_self_signed_is_rejected_by_default(self, https_server):
        with pytest.raises(httpx.ConnectError, match="CERTIFICATE_VERIFY_FAILED"):
            self._get(https_server, True)
