"""
Local Desktop Client Bridge for SAP BusinessObjects MCP Server.
Runs locally on macOS (Keychain) or Windows (Credential Manager), resolves credentials
from the local OS Keyring, and bridges standard STDIO MCP clients (Antigravity IDE,
Claude Desktop, Cursor) to a remote co-located bo-mcp server over Streamable HTTP or SSE.

Usage in local MCP configuration (macOS & Windows):
{
  "mcpServers": {
    "sap-business-objects": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/BO_MCP",
        "run", "python", "deploy/client_bridge.py",
        "--remote-url", "http://your-bo-host:8000"
      ]
    }
  }
}
"""

from __future__ import annotations

import argparse
import logging
import os
import ssl
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse

import anyio
import httpx
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.server.stdio import stdio_server
from mcp.shared.message import SessionMessage

# Ensure project root is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.auth.providers import ChainedCredentialProvider  # noqa: E402

# Set up logging to stderr only so JSON-RPC on stdout is never corrupted
logger = logging.getLogger("BOEClientBridge")
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [Bridge] %(message)s",
)


def resolve_desktop_headers(
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> Dict[str, str]:
    """
    Resolves SAP BusinessObjects credentials from explicit arguments,
    local .env, or the desktop OS Keyring (macOS Keychain / Windows Credential Manager).
    Returns custom headers for remote server session authentication.
    """
    provider = ChainedCredentialProvider()
    creds = provider.get_credentials() if (not username or not password) else None

    user = username or (creds.username if creds else None) or os.getenv("SAP_BO_USERNAME")
    pwd = password or (creds.get_password() if creds else None) or os.getenv("SAP_BO_PASSWORD")

    headers: Dict[str, str] = {}
    if user and pwd:
        headers["X-SAP-Username"] = user
        headers["X-SAP-Password"] = pwd
        logger.info(f"Resolved credentials from desktop Keyring/env for user '{user}'.")
    else:
        logger.warning(
            "No SAP BO credentials found in desktop Keyring or local .env. "
            "You can store them with 'python deploy/client_bridge.py configure' "
            "or log in manually via the 'login' tool in chat."
        )

    return headers


LOOPBACK_HOSTS = ("localhost", "127.0.0.1", "::1")


def resolve_tls_verify(ca_file: Optional[str] = None, insecure: bool = False) -> Union[bool, ssl.SSLContext]:
    """
    Resolves the httpx `verify` argument for the remote connection.

    - insecure=True disables certificate verification (development only).
    - ca_file trusts a private CA bundle or a self-signed server certificate.
    - otherwise the system trust store is used.
    """
    if insecure:
        logger.warning("TLS certificate verification is DISABLED (--insecure). Use for development only.")
        return False
    if ca_file:
        if not os.path.isfile(ca_file):
            raise FileNotFoundError(f"CA bundle not found: {ca_file}")
        return ssl.create_default_context(cafile=ca_file)
    return True


def warn_if_insecure_transport(remote_url: str, has_credentials: bool) -> None:
    """Warns when credentials are about to travel over plain HTTP to a non-loopback host."""
    parsed = urlparse(remote_url.strip())
    if parsed.scheme == "http" and has_credentials and (parsed.hostname or "") not in LOOPBACK_HOSTS:
        logger.warning(
            "Remote URL uses plain HTTP: your SAP BO password is sent unencrypted in request headers. "
            "Use https:// (see QUICKSTART/README) unless this is a trusted network."
        )


def make_httpx_client_factory(verify: Union[bool, ssl.SSLContext] = True) -> Any:
    """Returns an MCP-compatible httpx client factory honouring the TLS `verify` setting."""

    def factory(
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[httpx.Timeout] = None,
        auth: Optional[httpx.Auth] = None,
    ) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers=headers,
            timeout=timeout or httpx.Timeout(30.0, read=300.0),
            auth=auth,
            verify=verify,
            follow_redirects=True,
        )

    return factory


def format_endpoint_url(base_url: str, transport: str) -> str:
    """Normalizes the target remote URL to the FastMCP endpoint (/mcp or /sse)."""
    clean_url = base_url.strip().rstrip("/")
    if transport in ("streamable-http", "http"):
        if not clean_url.endswith("/mcp"):
            clean_url = f"{clean_url}/mcp"
    elif transport == "sse":
        if not clean_url.endswith("/sse"):
            clean_url = f"{clean_url}/sse"
    return clean_url


async def _pipe_stream(
    source_stream: Any,
    dest_stream: Any,
    direction: str,
    cancel_scope: anyio.CancelScope,
) -> None:
    """Forwards SessionMessages from source_stream to dest_stream until EOF or error."""
    try:
        async with source_stream:
            async for item in source_stream:
                if isinstance(item, Exception):
                    logger.debug(f"Stream exception in {direction}: {item}")
                    continue
                if isinstance(item, SessionMessage):
                    await dest_stream.send(item)
    except (anyio.ClosedResourceError, anyio.EndOfStream):
        logger.debug(f"{direction} reached End of Stream.")
    except Exception as e:
        logger.debug(f"Exception in {direction}: {e}")
    finally:
        cancel_scope.cancel()


async def run_bridge(
    remote_url: str,
    transport: str = "streamable-http",
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
    verify: Union[bool, ssl.SSLContext] = True,
) -> None:
    """
    Main asynchronous bridge loop:
    1. Listens on local stdio (for Antigravity IDE, Claude Desktop, Cursor)
    2. Connects to the remote server over Streamable HTTP or SSE
    3. Transparently forwards JSON-RPC messages bi-directionally
    """
    endpoint = format_endpoint_url(remote_url, transport)
    request_headers = headers or {}
    client_factory = make_httpx_client_factory(verify)

    logger.info(f"Connecting local desktop stdio to remote bo-mcp ({transport}) at: {endpoint}")

    async with stdio_server() as (local_in, local_out):
        if transport in ("streamable-http", "http"):
            async with streamablehttp_client(
                url=endpoint,
                headers=request_headers,
                timeout=timeout,
                httpx_client_factory=client_factory,
            ) as (remote_in, remote_out, get_session_id):
                session_id = get_session_id()
                if session_id:
                    logger.info(f"Established remote StreamableHTTP session: {session_id}")

                async with anyio.create_task_group() as tg:
                    tg.start_soon(
                        _pipe_stream,
                        local_in,
                        remote_out,
                        "client -> remote",
                        tg.cancel_scope,
                    )
                    tg.start_soon(
                        _pipe_stream,
                        remote_in,
                        local_out,
                        "remote -> client",
                        tg.cancel_scope,
                    )
        elif transport == "sse":
            async with sse_client(
                url=endpoint,
                headers=request_headers,
                timeout=timeout,
                httpx_client_factory=client_factory,
            ) as (remote_in, remote_out):
                logger.info("Established remote SSE connection.")
                async with anyio.create_task_group() as tg:
                    tg.start_soon(
                        _pipe_stream,
                        local_in,
                        remote_out,
                        "client -> remote",
                        tg.cancel_scope,
                    )
                    tg.start_soon(
                        _pipe_stream,
                        remote_in,
                        local_out,
                        "remote -> client",
                        tg.cancel_scope,
                    )
        else:
            raise ValueError(f"Unsupported transport protocol: {transport}")


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local Desktop Client Bridge for SAP BusinessObjects MCP Server")
    parser.add_argument(
        "--remote-url",
        default=os.getenv("SAP_BO_REMOTE_URL") or os.getenv("MCP_REMOTE_URL") or "http://localhost:8000",
        help="Remote bo-mcp server URL (default: http://localhost:8000 or SAP_BO_REMOTE_URL env var)",
    )
    parser.add_argument(
        "--transport",
        choices=["streamable-http", "http", "sse"],
        default="streamable-http",
        help="Transport protocol (default: streamable-http)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP connection timeout in seconds (default: 30.0)",
    )
    parser.add_argument(
        "--ca-file",
        default=os.getenv("SAP_BO_CA_FILE", "").strip() or None,
        help="PEM CA bundle (or the self-signed server certificate) to trust for https:// URLs "
        "(default: SAP_BO_CA_FILE env var)",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        default=os.getenv("SAP_BO_TLS_INSECURE", "").strip().lower() in ("1", "true", "yes"),
        help="Disable TLS certificate verification (DEVELOPMENT ONLY)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> None:
    args_list = sys.argv[1:] if argv is None else argv

    # Support credential management subcommands directly from the desktop bridge
    if len(args_list) > 0 and args_list[0] in ("configure", "setup", "test", "clear", "status"):
        from core.auth.cli import main as auth_cli_main

        sys.exit(auth_cli_main(args_list))

    parsed = parse_args(args_list)
    headers = resolve_desktop_headers()
    warn_if_insecure_transport(parsed.remote_url, bool(headers))

    try:
        verify = resolve_tls_verify(parsed.ca_file, parsed.insecure)
        anyio.run(run_bridge, parsed.remote_url, parsed.transport, headers, parsed.timeout, verify)
    except KeyboardInterrupt:
        logger.info("Bridge stopped by user.")
    except Exception as e:
        logger.error(f"Bridge fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
