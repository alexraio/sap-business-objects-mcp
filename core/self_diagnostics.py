"""
Self-Diagnostics, Health Probing, and Internal Log Ring-Buffer for SAP BusinessObjects MCP Server.
Enables AI agents and administrators to troubleshoot remote HTTP/SSE deployments directly over MCP
or via the `python server.py doctor` CLI command without requiring SSH access first.
"""

from __future__ import annotations

import collections
import datetime as dt
import getpass
import json
import logging
import os
import platform
import re
import socket
import subprocess
import sys
import threading
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING, Any, Deque, Dict, List, Optional

import requests

if TYPE_CHECKING:
    from core.session import SessionManager, UserSession

SECRET_MASK_PATTERNS = (
    re.compile(r"(PWD\s*=\s*)([^;\"'\s]+)", re.IGNORECASE),
    re.compile(r"(password['\"\s:=]+)([^;\"'\s,}]+)", re.IGNORECASE),
    re.compile(r"(X-SAP-LogonToken['\"\s:=]+)([^\"'\r\n]+)", re.IGNORECASE),
)


def sanitize_log_text(text: str) -> str:
    """Masks passwords and SAP logon tokens from internal log lines."""
    masked = text
    for pattern in SECRET_MASK_PATTERNS:
        masked = pattern.sub(r"\1**********", masked)
    return masked


class InMemoryRingBufferHandler(logging.Handler):
    """
    Thread-safe in-memory ring buffer capturing recent server log events and tracebacks
    so remote AI agents can inspect internal server errors via `get_mcp_server_diagnostics`.
    """

    def __init__(self, maxlen: int = 200):
        super().__init__(level=logging.INFO)
        self._records: Deque[Dict[str, str]] = collections.deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            if record.exc_info and not record.exc_text:
                msg = f"{msg}\n{self.formatter.formatException(record.exc_info) if self.formatter else ''}"
            entry = {
                "timestamp": dt.datetime.fromtimestamp(record.created, tz=dt.timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": sanitize_log_text(msg.strip()),
            }
            with self._lock:
                self._records.append(entry)
        except Exception:
            self.handleError(record)

    def get_recent(self, limit: int = 50, min_level: Optional[str] = None) -> List[Dict[str, str]]:
        """Returns the most recent log records (newest last), optionally filtered by minimum level."""
        level_num = getattr(logging, min_level.upper(), logging.INFO) if min_level else logging.INFO
        with self._lock:
            items = [r for r in self._records if getattr(logging, r["level"], logging.INFO) >= level_num]
        return items[-max(1, min(limit, 200)) :]


# Global singleton ring buffer attached on server import
ring_buffer_handler = InMemoryRingBufferHandler(maxlen=200)


def configure_server_logging(log_file_path: Optional[Path] = None) -> None:
    """
    Attaches the in-memory ring buffer handler and an optional rotating file handler
    to the root and BO_MCP domain loggers.
    """
    root_logger = logging.getLogger()
    if root_logger.level == logging.NOTSET or root_logger.level > logging.INFO:
        root_logger.setLevel(logging.INFO)

    if ring_buffer_handler not in root_logger.handlers:
        root_logger.addHandler(ring_buffer_handler)

    target_file = log_file_path
    if target_file is None:
        env_file = os.getenv("MCP_SERVER_LOG_FILE")
        if env_file:
            target_file = Path(env_file)

    if target_file is not None:
        try:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                target_file,
                maxBytes=5 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
            root_logger.addHandler(file_handler)
        except OSError:
            pass


_AUDIT_PROBE_SCRIPT = r"""
import faulthandler, json, sys, time
faulthandler.enable()
sys.path.insert(0, sys.argv[1])

def emit(**kw):
    print(json.dumps(kw), flush=True)

import core.session  # noqa: F401  (same import order as server.py; avoids a circular import)
from services import audit_service as a

mod = a._load_pyodbc()
if mod is None:
    emit(
        stage="import",
        pyodbc_installed=False,
        error="pyodbc is not installed or the unixODBC library is missing on this host "
        "(install with 'uv sync --extra audit' and the unixODBC package).",
    )
    sys.exit(0)
emit(stage="import", pyodbc_installed=True)
try:
    drivers = list(mod.drivers())
except Exception:
    drivers = []
emit(stage="drivers", available_odbc_drivers=drivers)
t = time.perf_counter()
try:
    a.AuditService().execute_query("SELECT 1 AS health_check", max_rows=1)
    emit(stage="query", connected=True, latency_ms=round((time.perf_counter() - t) * 1000.0, 2))
except Exception as e:
    emit(stage="query", connected=False, latency_ms=round((time.perf_counter() - t) * 1000.0, 2), error=str(e))
"""


def probe_audit_database(timeout_seconds: Optional[float] = None) -> Dict[str, Any]:
    """
    Probes the Auditing DB ODBC stack in a child process.

    A segfault/abort in unixODBC or the vendor driver, or a network hang, would otherwise kill or freeze
    the whole server (and make `doctor` print nothing). Here it is reported as a readable error instead.
    """
    try:
        db_timeout = max(5, int(os.getenv("SAP_BO_AUDIT_TIMEOUT", "20")))
    except ValueError:
        db_timeout = 20
    limit = timeout_seconds if timeout_seconds is not None else db_timeout + 10

    probe: Dict[str, Any] = {
        "pyodbc_installed": None,
        "available_odbc_drivers": [],
        "odbcini_env": os.getenv("ODBCINI"),
        "ld_library_path_set": bool(os.getenv("LD_LIBRARY_PATH")),
        "configured_dsn": os.getenv("SAP_BO_AUDIT_DSN"),
        "configured_host": os.getenv("SAP_BO_AUDIT_HOST"),
        "configured_user": os.getenv("SAP_BO_AUDIT_USER"),
        "connected": False,
        "latency_ms": None,
        "error": None,
    }
    project_root = str(Path(__file__).resolve().parent.parent)
    t0 = time.perf_counter()
    stdout, stderr, returncode, timed_out = "", "", 0, False
    try:
        proc = subprocess.run(
            [sys.executable, "-c", _AUDIT_PROBE_SCRIPT, project_root],
            capture_output=True,
            text=True,
            timeout=limit,
            cwd=project_root,
            env=os.environ.copy(),
        )
        stdout, stderr, returncode = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as e:
        timed_out = True
        stdout = e.stdout.decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        stderr = e.stderr.decode(errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
    except Exception as e:
        probe["error"] = sanitize_log_text(f"Could not start audit probe subprocess: {e}")
        return probe

    # Merge the progressive JSON lines emitted by the child (so partial results survive a crash).
    for line in stdout.splitlines():
        try:
            data = json.loads(line)
        except ValueError:
            continue
        data.pop("stage", None)
        probe.update(data)
    if probe.get("latency_ms") is None:
        probe["latency_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

    stderr_tail = sanitize_log_text(" | ".join(stderr.strip().splitlines()[-6:]))
    if timed_out:
        probe["connected"] = False
        probe["error"] = (
            f"Audit DB probe timed out after {limit:.0f}s (ODBC driver or database network hang). "
            f"Check SAP_BO_AUDIT_DSN host/port reachability and the driver. {stderr_tail}"
        ).strip()
    elif returncode != 0:
        probe["connected"] = False
        reason = f"signal {-returncode}" if returncode < 0 else f"exit code {returncode}"
        probe["error"] = (
            f"Audit DB probe process crashed ({reason}) - likely a native ODBC library/driver problem "
            f"(check LD_LIBRARY_PATH/ODBCINI and driver architecture). {stderr_tail}"
        ).strip()
    elif probe.get("error"):
        probe["error"] = sanitize_log_text(str(probe["error"]))
    return probe


def collect_server_diagnostics(
    session: "UserSession",
    session_manager: "SessionManager",
    include_recent_logs: bool = True,
    max_log_lines: int = 50,
) -> Dict[str, Any]:
    """
    Executes a comprehensive non-destructive health and configuration probe across all 4 subsystems:
    1. Runtime & Session state (OS, Python, transport mode, active sessions, RBAC status)
    2. SAP BusinessObjects REST Web Services (`biprws/logon/long` reachability & latency)
    3. Local SAP BO Log Directory (`SAP_BO_LOG_DIR` existence, permissions, and file count)
    4. Auditing Database ODBC Connector (`pyodbc` availability, `ODBCINI`, drivers, and live ping)
    """
    # 1. Runtime & Session Info
    try:
        proc_user = getpass.getuser()
    except Exception:
        proc_user = "unknown"

    runtime_info: Dict[str, Any] = {
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "os_system": platform.system(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "process_user": proc_user,
        "working_directory": str(Path.cwd()),
        "remote_mode": session_manager.remote_mode,
        "active_sessions_count": session_manager.get_active_sessions_count(),
        "current_session": {
            "session_id": session.session_id,
            "authenticated_user": session.authenticated_user,
            "is_authenticated": session.is_authenticated,
            "is_admin": session.is_admin,
        },
    }

    # 2. SAP BO REST API (biprws) Reachability Probe
    bip_url = session.parser.bip_url
    rest_probe: Dict[str, Any] = {
        "configured_bip_url": bip_url,
        "reachable": False,
        "status_code": None,
        "latency_ms": None,
        "error": None,
    }
    t0 = time.perf_counter()
    try:
        resp = requests.get(
            f"{bip_url}/logon/long",
            headers={"Accept": "application/json"},
            timeout=5,
        )
        rest_probe["latency_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
        rest_probe["status_code"] = resp.status_code
        rest_probe["reachable"] = resp.status_code in (200, 401, 405)
        if not rest_probe["reachable"]:
            rest_probe["error"] = f"Unexpected HTTP status {resp.status_code} from {bip_url}/logon/long"
    except Exception as e:
        rest_probe["latency_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
        rest_probe["error"] = sanitize_log_text(str(e))

    # 3. Local SAP BO Log Directory Probe
    log_probe: Dict[str, Any] = {
        "configured_env_path": os.getenv("SAP_BO_LOG_DIR"),
        "resolved_path": None,
        "status": "unconfigured",
        "readable": False,
        "recent_files_24h": 0,
        "error": None,
    }
    try:
        resolved_dir = session.parser.logs._get_log_dir()
        log_probe["resolved_path"] = str(resolved_dir)
        log_probe["readable"] = os.access(resolved_dir, os.R_OK)
        listing = session.parser.logs.list_log_files(hours_back=24, max_files=100)
        log_probe["recent_files_24h"] = listing["total_matching_files"]
        log_probe["status"] = "ok" if log_probe["readable"] else "permission_denied"
    except Exception as e:
        log_probe["status"] = "error"
        log_probe["error"] = sanitize_log_text(str(e))

    # 4. Auditing Database ODBC Probe (isolated in a subprocess: native ODBC libraries can crash or hang)
    audit_probe = probe_audit_database()

    result: Dict[str, Any] = {
        "runtime": runtime_info,
        "subsystems": {
            "sap_bo_rest_api": rest_probe,
            "local_log_service": log_probe,
            "auditing_db_odbc": audit_probe,
        },
    }

    if include_recent_logs:
        result["recent_internal_logs"] = ring_buffer_handler.get_recent(limit=max_log_lines)

    return result
