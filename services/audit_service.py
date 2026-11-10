"""
SAP BusinessObjects Auditing Database Direct ODBC Service (AuditService).
Provides RDBMS-agnostic, strictly read-only introspection of SAP BO 4.3 ADS_* auditing tables
via native host ODBC connections (Linux unixODBC / Windows ODBC Data Source Administrator).
"""

from __future__ import annotations

import datetime as dt
import logging
import os
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Optional, Sequence

from pydantic import SecretStr

from core.exceptions import BOEAuditDBError

# pyodbc is imported lazily: loading it pulls in native libraries (unixODBC), and a broken
# library path must never be able to take down the whole server or the `doctor` CLI at import time.
pyodbc: Any = None
_PYODBC_IMPORT_ATTEMPTED = False

logger = logging.getLogger("AuditService")


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

    def __init__(self, config: Optional[AuditDBConfig] = None):
        self.config = config

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
        if val is None or isinstance(val, (str, int, float, bool)):
            return val
        if isinstance(val, (dt.datetime, dt.date, dt.time)):
            return val.isoformat()
        if isinstance(val, Decimal):
            return float(val)
        if isinstance(val, (bytes, bytearray)):
            return val.decode("utf-8", errors="replace")
        return str(val)

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

        odbc = _load_pyodbc()
        if odbc is None:
            raise BOEAuditDBError(
                "pyodbc is not installed or unixODBC library is missing on this host. "
                "Install unixODBC and pyodbc to query the SAP BusinessObjects Auditing Database."
            )

        capped_max = max(1, min(max_rows, self.MAX_ALLOWED_ROWS))

        try:
            with odbc.connect(conn_str, readonly=True, timeout=cfg.timeout) as conn:
                with conn.cursor() as cursor:
                    if params:
                        cursor.execute(validated_sql, tuple(params))
                    else:
                        cursor.execute(validated_sql)

                    if not cursor.description:
                        return {
                            "query": validated_sql,
                            "columns": [],
                            "rows_returned": 0,
                            "is_truncated": False,
                            "rows": [],
                        }

                    columns = [col[0] for col in cursor.description]
                    raw_rows = cursor.fetchmany(capped_max + 1)
                    is_truncated = len(raw_rows) > capped_max
                    selected_rows = raw_rows[:capped_max]

                    rows = [
                        {col: self._serialize_value(val) for col, val in zip(columns, row)} for row in selected_rows
                    ]

                    return {
                        "query": validated_sql,
                        "columns": columns,
                        "rows_returned": len(rows),
                        "max_rows": capped_max,
                        "is_truncated": is_truncated,
                        "rows": rows,
                    }
        except BOEAuditDBError:
            raise
        except Exception as e:
            raise BOEAuditDBError(f"Auditing Database ODBC query failed: {e}") from e

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
