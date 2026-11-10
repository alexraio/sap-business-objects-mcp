"""
Standalone ODBC query worker for the SAP BusinessObjects Auditing Database.

Runs in a *child process* of the MCP server (`python services/audit_worker.py`), reading one JSON
request from stdin and writing one result line to stdout. Isolating ODBC this way means that a native
crash (SIGSEGV in unixODBC / a vendor driver) or a network hang cannot take the MCP server down, and
lets the parent control LD_LIBRARY_PATH for the driver independently of how the server was started.

This module must stay importable with the standard library only (it is executed as a plain script),
while `run_query` is also reused in-process by `AuditService` when isolation is disabled.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from decimal import Decimal
from typing import Any, Dict, Optional, Sequence

RESULT_MARKER = "@@BO_MCP_AUDIT_RESULT@@"


def serialize_value(val: Any) -> Any:
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


def run_query(
    odbc: Any,
    conn_str: str,
    sql: str,
    params: Optional[Sequence[Any]],
    capped_max: int,
    timeout: int,
) -> Dict[str, Any]:
    """Executes an already-validated read-only query and returns capped, JSON-safe rows."""
    with odbc.connect(conn_str, readonly=True, timeout=timeout) as conn:
        with conn.cursor() as cursor:
            if params:
                cursor.execute(sql, tuple(params))
            else:
                cursor.execute(sql)

            if not cursor.description:
                return {"columns": [], "rows_returned": 0, "is_truncated": False, "rows": []}

            columns = [col[0] for col in cursor.description]
            raw_rows = cursor.fetchmany(capped_max + 1)
            is_truncated = len(raw_rows) > capped_max
            rows = [{col: serialize_value(val) for col, val in zip(columns, row)} for row in raw_rows[:capped_max]]
            return {
                "columns": columns,
                "rows_returned": len(rows),
                "max_rows": capped_max,
                "is_truncated": is_truncated,
                "rows": rows,
            }


def _emit(payload: Dict[str, Any]) -> None:
    sys.stdout.write(f"\n{RESULT_MARKER}{json.dumps(payload)}\n")
    sys.stdout.flush()


def main() -> int:
    import faulthandler

    faulthandler.enable()  # a native crash leaves a Python traceback on stderr for the parent to report
    request = json.load(sys.stdin)
    try:
        import pyodbc  # type: ignore[import-not-found]
    except ImportError as e:
        _emit({"error_code": "pyodbc_missing", "error": str(e)})
        return 0

    try:
        result = run_query(
            pyodbc,
            request["conn_str"],
            request["sql"],
            request.get("params"),
            int(request["capped_max"]),
            int(request["timeout"]),
        )
        _emit({"result": result})
    except Exception as e:  # noqa: BLE001 - reported to the parent as a structured error
        _emit({"error_code": "query_failed", "error": str(e)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
