"""
SAP BusinessObjects Auditing Database Direct ODBC Service (AuditService).
Provides RDBMS-agnostic, strictly read-only introspection of SAP BO 4.3 ADS_* auditing tables
via native host ODBC connections (Linux unixODBC / Windows ODBC Data Source Administrator).
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from pydantic import SecretStr

from core.exceptions import BOEAuditDBError
from services.audit_worker import RESULT_MARKER, run_query, serialize_value

# pyodbc is imported lazily: loading it pulls in native libraries (unixODBC), and a broken
# library path must never be able to take down the whole server or the `doctor` CLI at import time.
pyodbc: Any = None
_PYODBC_IMPORT_ATTEMPTED = False

logger = logging.getLogger("AuditService")


WORKER_PATH = Path(__file__).resolve().parent / "audit_worker.py"
SYSTEM_LIB_DIRS = ("/usr/lib64", "/usr/lib/x86_64-linux-gnu", "/usr/lib")
DEFAULT_SQLANYWHERE_HOMES = ("/opt/bobj/sqlanywhere", "/opt/sqlanywhere17")
PASSWORD_IN_TEXT_RE = re.compile(r"(PWD\s*=\s*)([^;\s'\"]+)", re.IGNORECASE)


def build_odbc_env(base_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Builds the environment for the ODBC worker/probe child process (Linux only; a copy of the input).

    SAP BO host profiles typically export an LD_LIBRARY_PATH containing the DataDirect `libodbc.so` /
    `libodbcinst.so` (and vendor client dirs). Those shadow the unixODBC libraries that pyodbc is linked
    against and make the driver segfault. Here the system library directories are put FIRST, the SQL
    Anywhere client libraries next, and the original entries last. SQLANY17 is also set when missing
    (without it the SQL Anywhere driver fails with IM004 "SQLAllocHandle on SQL_HANDLE_HENV failed").
    Override the SQL Anywhere location with SAP_BO_SQLANYWHERE_HOME.
    """
    env = dict(os.environ if base_env is None else base_env)
    if not sys.platform.startswith("linux"):
        return env

    sa_home = next(
        (
            c
            for c in (
                env.get("SAP_BO_SQLANYWHERE_HOME"),
                env.get("SQLANY17"),
                *DEFAULT_SQLANYWHERE_HOMES,
            )
            if c and os.path.isdir(c)
        ),
        None,
    )

    leading = [d for d in SYSTEM_LIB_DIRS if os.path.isdir(d)]
    if sa_home:
        sa_lib = os.path.join(sa_home, "lib64")
        if os.path.isdir(sa_lib):
            leading.append(sa_lib)
        env.setdefault("SQLANY17", sa_home)

    original = [d for d in env.get("LD_LIBRARY_PATH", "").split(":") if d]
    merged: list[str] = []
    for entry in (*leading, *original):
        if entry not in merged:
            merged.append(entry)
    env["LD_LIBRARY_PATH"] = ":".join(merged)
    return env


def _mask_secrets(text: str, password: Optional[str]) -> str:
    """Removes the audit DB password (literal and PWD=... forms) from text destined for logs/errors."""
    if password:
        text = text.replace(password, "**********")
    return PASSWORD_IN_TEXT_RE.sub(r"\1**********", text)


def _load_pyodbc() -> Any:
    """Imports pyodbc on first use. Returns the module, or None if it (or unixODBC) is unavailable."""
    global pyodbc, _PYODBC_IMPORT_ATTEMPTED
    if pyodbc is None and not _PYODBC_IMPORT_ATTEMPTED:
        _PYODBC_IMPORT_ATTEMPTED = True
        try:
            import pyodbc as _pyodbc  # type: ignore[import-not-found]

            pyodbc = _pyodbc
        except ImportError as e:
            logger.warning("pyodbc could not be imported: %s", e)
    return pyodbc


FORBIDDEN_SQL_KEYWORDS = frozenset(
    {
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "TRUNCATE",
        "CREATE",
        "REPLACE",
        "MERGE",
        "GRANT",
        "REVOKE",
        "EXEC",
        "EXECUTE",
        "CALL",
        "COMMIT",
        "ROLLBACK",
        "INTO",
        "ATTACH",
        "DETACH",
        "SHUTDOWN",
    }
)

SQL_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
SQL_LINE_COMMENT_RE = re.compile(r"--[^\r\n]*")
SQL_STRING_LITERAL_RE = re.compile(r"'(?:''|[^'])*'")
SQL_WORD_TOKEN_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")


@dataclass
class AuditDBConfig:
    """
    Configuration for the SAP BusinessObjects Auditing Database ODBC connection.
    Supports pre-configured system DSNs (Linux odbc.ini / Windows ODBC) or explicit connection strings.
    """

    dsn: Optional[str] = None
    connection_string: Optional[str] = None
    driver: Optional[str] = None
    host: Optional[str] = None
    port: int = 2638
    database: str = "BI4_Audit"
    server_name: Optional[str] = None
    user: Optional[str] = None
    password: Optional[SecretStr] = None
    timeout: int = 20

    @classmethod
    def from_env(cls) -> "AuditDBConfig":
        """Loads Auditing Database ODBC settings from environment variables."""
        raw_pwd = os.getenv("SAP_BO_AUDIT_PASSWORD")
        raw_port = os.getenv("SAP_BO_AUDIT_PORT", "2638")
        raw_timeout = os.getenv("SAP_BO_AUDIT_TIMEOUT", "20")

        try:
            port = int(raw_port)
        except ValueError:
            port = 2638

        try:
            timeout = max(5, int(raw_timeout))
        except ValueError:
            timeout = 20

        return cls(
            dsn=os.getenv("SAP_BO_AUDIT_DSN") or None,
            connection_string=os.getenv("SAP_BO_AUDIT_CONNECTION_STRING") or None,
            driver=os.getenv("SAP_BO_AUDIT_DRIVER") or None,
            host=os.getenv("SAP_BO_AUDIT_HOST") or None,
            port=port,
            database=os.getenv("SAP_BO_AUDIT_DB", "BI4_Audit"),
            server_name=os.getenv("SAP_BO_AUDIT_SERVER") or None,
            user=os.getenv("SAP_BO_AUDIT_USER") or None,
            password=SecretStr(raw_pwd) if raw_pwd else None,
            timeout=timeout,
        )

    def build_connection_string(self) -> str:
        """
        Builds the ODBC connection string from explicit override, System DSN, or driver+host settings.
        Raises BOEAuditDBError if neither DSN nor connection_string/driver is configured.
        """
        if self.connection_string and self.connection_string.strip():
            return self.connection_string.strip()

        pwd = self.password.get_secret_value() if self.password else None

        if self.dsn and self.dsn.strip():
            parts = [f"DSN={self.dsn.strip()}"]
            if self.user:
                parts.append(f"UID={self.user.strip()}")
            if pwd:
                parts.append(f"PWD={pwd}")
            return ";".join(parts)

        if self.driver and self.host:
            drv = self.driver.strip()
            if not drv.startswith("{"):
                drv = f"{{{drv}}}"
            parts = [
                f"Driver={drv}",
                f"Database={self.database}",
            ]
            if self.server_name:
                parts.append(f"ENG={self.server_name.strip()}")
                parts.append(f"DBN={self.database}")
                parts.append(f"LINKS=tcpip(host={self.host.strip()};port={self.port})")
            else:
                parts.append(f"Server={self.host.strip()},{self.port}")
            if self.user:
                parts.append(f"UID={self.user.strip()}")
            if pwd:
                parts.append(f"PWD={pwd}")
            return ";".join(parts)

        raise BOEAuditDBError(
            "SAP BusinessObjects Auditing Database ODBC connection is not configured. "
            "Set SAP_BO_AUDIT_DSN (plus SAP_BO_AUDIT_USER and SAP_BO_AUDIT_PASSWORD) "
            "or SAP_BO_AUDIT_CONNECTION_STRING in your .env or service environment."
        )


class AuditService:
    """
    Service for querying the SAP BusinessObjects 4.3 Auditing Database (ADS_* schema) via ODBC.
    Enforces read-only SQL execution, query timeouts, and RDBMS-agnostic row capping.
    """

    MAX_ALLOWED_ROWS = 1000

    def __init__(self, config: Optional[AuditDBConfig] = None, isolated: Optional[bool] = None):
        """
        Args:
            config: Explicit ODBC settings (defaults to environment variables).
            isolated: Run ODBC in a child process (default; env SAP_BO_AUDIT_ISOLATED=false disables).
                In-process mode is only meant for debugging; a native driver crash would kill the server.
        """
        self.config = config
        self.isolated = (
            isolated
            if isolated is not None
            else os.getenv("SAP_BO_AUDIT_ISOLATED", "true").strip().lower() not in ("0", "false", "no")
        )

    def _get_config(self) -> AuditDBConfig:
        return self.config or AuditDBConfig.from_env()

    @staticmethod
    def validate_readonly_sql(sql: str) -> str:
        """
        Validates that a SQL statement is strictly a single, read-only SELECT or WITH query.
        Strips SQL comments, blocks multi-statement semicolons, and rejects any DML/DDL/DCL keywords.
        """
        if not sql or not sql.strip():
            raise BOEAuditDBError("SQL query cannot be empty.")

        # Strip block and single-line comments
        no_comments = SQL_BLOCK_COMMENT_RE.sub(" ", sql)
        no_comments = SQL_LINE_COMMENT_RE.sub(" ", no_comments).strip()

        # Strip a single optional trailing semicolon
        if no_comments.endswith(";"):
            no_comments = no_comments[:-1].strip()

        if not no_comments:
            raise BOEAuditDBError("SQL query contains no executable statement after removing comments.")

        # Mask string literals before checking for embedded semicolons or forbidden keywords
        masked = SQL_STRING_LITERAL_RE.sub("''", no_comments)

        if ";" in masked:
            raise BOEAuditDBError(
                "Security violation: Multi-statement SQL queries (containing ';') are forbidden on the Auditing Database."
            )

        tokens = [t.upper() for t in SQL_WORD_TOKEN_RE.findall(masked)]
        if not tokens or tokens[0] not in ("SELECT", "WITH"):
            raise BOEAuditDBError(
                "Security violation: Only read-only SELECT (or WITH ... SELECT) queries are permitted on the Auditing Database."
            )

        for token in tokens:
            if token in FORBIDDEN_SQL_KEYWORDS:
                raise BOEAuditDBError(
                    f"Security violation: Forbidden SQL keyword '{token}' detected. "
                    "The Auditing Database connector is strictly read-only."
                )

        return no_comments

    @staticmethod
    def _serialize_value(val: Any) -> Any:
        """Converts database driver values into JSON-serializable Python types."""
        return serialize_value(val)

    def _run_isolated(
        self,
        cfg: AuditDBConfig,
        conn_str: str,
        sql: str,
        params: Optional[Sequence[Any]],
        capped_max: int,
    ) -> Dict[str, Any]:
        """Executes the query in a child process with a controlled library environment."""
        secret = cfg.password.get_secret_value() if cfg.password else None
        limit = cfg.timeout + 15
        request = json.dumps(
            {
                "conn_str": conn_str,
                "sql": sql,
                "params": list(params) if params else None,
                "capped_max": capped_max,
                "timeout": cfg.timeout,
            }
        )
        try:
            proc = subprocess.run(
                [sys.executable, str(WORKER_PATH)],
                input=request,
                capture_output=True,
                text=True,
                timeout=limit,
                env=build_odbc_env(),
            )
        except subprocess.TimeoutExpired as e:
            raise BOEAuditDBError(
                f"Auditing Database query timed out after {limit}s (ODBC driver or network hang). "
                "Verify the DSN host/port and that the database server is running."
            ) from e

        stderr_tail = _mask_secrets(" | ".join(proc.stderr.strip().splitlines()[-6:]), secret)
        if proc.returncode != 0:
            reason = f"signal {-proc.returncode}" if proc.returncode < 0 else f"exit code {proc.returncode}"
            raise BOEAuditDBError(
                f"Auditing Database ODBC worker crashed ({reason}) - likely a native ODBC library/driver problem "
                f"(check ODBCINI, driver architecture and library path). {stderr_tail}".strip()
            )

        payload: Optional[Dict[str, Any]] = None
        for line in proc.stdout.splitlines():
            if line.startswith(RESULT_MARKER):
                try:
                    payload = json.loads(line[len(RESULT_MARKER) :])
                except ValueError:
                    payload = None
        if payload is None:
            raise BOEAuditDBError(f"Auditing Database ODBC worker returned no result. {stderr_tail}".strip())
        if payload.get("error_code") == "pyodbc_missing":
            raise BOEAuditDBError(
                "pyodbc is not installed or unixODBC library is missing on this host. "
                "Install it with 'uv sync --extra audit' and the unixODBC package."
            )
        if "error" in payload:
            raise BOEAuditDBError(f"Auditing Database ODBC query failed: {_mask_secrets(payload['error'], secret)}")
        return payload["result"]

    def execute_query(
        self,
        sql_query: str,
        params: Optional[Sequence[Any]] = None,
        max_rows: int = 100,
    ) -> Dict[str, Any]:
        """
        Validates and executes a read-only SQL query against the SAP BO Auditing Database via ODBC.
        Caps returned rows using cursor.fetchmany(max_rows) for full RDBMS dialect portability.
        """
        validated_sql = self.validate_readonly_sql(sql_query)
        cfg = self._get_config()
        conn_str = cfg.build_connection_string()

        capped_max = max(1, min(max_rows, self.MAX_ALLOWED_ROWS))

        if self.isolated:
            result = self._run_isolated(cfg, conn_str, validated_sql, params, capped_max)
        else:
            odbc = _load_pyodbc()
            if odbc is None:
                raise BOEAuditDBError(
                    "pyodbc is not installed or unixODBC library is missing on this host. "
                    "Install it with 'uv sync --extra audit' and the unixODBC package."
                )
            try:
                result = run_query(odbc, conn_str, validated_sql, params, capped_max, cfg.timeout)
            except BOEAuditDBError:
                raise
            except Exception as e:
                raise BOEAuditDBError(f"Auditing Database ODBC query failed: {e}") from e

        return {"query": validated_sql, **result}

    # =========================================================================
    # High-Level SAP BO 4.3 Auditing Diagnostic Queries (ADS_* Schema)
    # =========================================================================

    def get_failed_events(
        self,
        hours_back: int = 24,
        event_type_id: Optional[int] = None,
        max_rows: int = 100,
    ) -> Dict[str, Any]:
        """
        Retrieves failed SAP BusinessObjects audit events from ADS_EVENT within the specified time window.
        Supports optional filtering by Event_Type_ID (e.g. 1002=View, 1003=Refresh, 1011=Run/Schedule, 1014=Logon).
        """
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=max(1, hours_back))
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")

        where_clauses = [
            f"e.Start_Time >= '{cutoff_str}'",
            "(e.Status_ID <> 0 OR (e.Error_Code IS NOT NULL AND e.Error_Code <> ''))",
        ]
        if event_type_id is not None:
            where_clauses.append(f"e.Event_Type_ID = {int(event_type_id)}")

        where_sql = " AND ".join(where_clauses)
        sql = (
            "SELECT e.Event_ID, e.Start_Time, e.Duration_ms, e.User_Name, "
            "e.Event_Type_ID, e.Status_ID, e.Object_ID, e.Object_Name, e.Error_Code, e.Server_CUID "
            f"FROM ADS_EVENT e WHERE {where_sql} ORDER BY e.Start_Time DESC"
        )
        res = self.execute_query(sql, max_rows=max_rows)
        res["hours_back"] = hours_back
        res["event_type_id"] = event_type_id
        return res

    def get_heavy_reports(
        self,
        days_back: int = 7,
        top_n: int = 20,
    ) -> Dict[str, Any]:
        """
        Identifies the slowest and heaviest reports recorded in ADS_EVENT over the last N days,
        ranked by maximum and average execution duration (Duration_ms).
        """
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=max(1, days_back))
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")

        sql = (
            "SELECT e.Object_ID, e.Object_Name, "
            "COUNT(*) AS Execution_Count, "
            "MAX(e.Duration_ms) AS Max_Duration_ms, "
            "AVG(e.Duration_ms) AS Avg_Duration_ms "
            "FROM ADS_EVENT e "
            f"WHERE e.Start_Time >= '{cutoff_str}' "
            "AND e.Object_Name IS NOT NULL AND e.Duration_ms > 0 "
            "GROUP BY e.Object_ID, e.Object_Name "
            "ORDER BY MAX(e.Duration_ms) DESC"
        )
        res = self.execute_query(sql, max_rows=max(1, min(top_n, 100)))
        res["days_back"] = days_back
        return res

    def get_user_activity(
        self,
        username: Optional[str] = None,
        hours_back: int = 24,
        max_rows: int = 100,
    ) -> Dict[str, Any]:
        """
        Retrieves recent user activity from ADS_EVENT (logons, document views, refreshes, exports).
        """
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=max(1, hours_back))
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")

        where_clauses = [f"e.Start_Time >= '{cutoff_str}'"]
        if username and username.strip():
            escaped_user = username.strip().replace("'", "''")
            where_clauses.append(f"e.User_Name = '{escaped_user}'")

        where_sql = " AND ".join(where_clauses)
        sql = (
            "SELECT e.Event_ID, e.Start_Time, e.Duration_ms, e.User_Name, "
            "e.Event_Type_ID, e.Status_ID, e.Object_ID, e.Object_Name, e.Error_Code "
            f"FROM ADS_EVENT e WHERE {where_sql} ORDER BY e.Start_Time DESC"
        )
        res = self.execute_query(sql, max_rows=max_rows)
        res["username_filter"] = username
        res["hours_back"] = hours_back
        return res
