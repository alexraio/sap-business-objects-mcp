"""
Local SAP BusinessObjects Server Log Analysis Service (LogService).
Provides sandboxed, reverse-chunked streaming inspection of SAP BO trace logs (.glf, .log, .trc)
across Linux and Windows hosts without loading large log files into memory.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from core.exceptions import BOELogError

logger = logging.getLogger("LogService")

DEFAULT_LINUX_LOG_DIRS = (
    "/opt/bobj/sap_bobj/logging",
    "/sap_bobj/logging",
    "/usr/sap/BO/sap_bobj/logging",
)
DEFAULT_WINDOWS_LOG_DIRS = (
    r"C:\Program Files (x86)\SAP BusinessObjects\SAP BusinessObjects Enterprise XI 4.0\logging",
    r"D:\Program Files (x86)\SAP BusinessObjects\SAP BusinessObjects Enterprise XI 4.0\logging",
)
SUPPORTED_LOG_EXTENSIONS = {".glf", ".log", ".trc", ".out"}

SEVERITY_NORMALIZATION = {
    "F": "Fatal",
    "FATAL": "Fatal",
    "E": "Error",
    "ERROR": "Error",
    "ERR": "Error",
    "S": "Error",
    "SEVERE": "Error",
    "W": "Warning",
    "WARN": "Warning",
    "WARNING": "Warning",
    "I": "Info",
    "INFO": "Info",
    "INFORMATION": "Info",
    "D": "Debug",
    "DEBUG": "Debug",
}

GLF_HEADER_PREFIXES = (
    "FILE_TYPE:",
    "ENCODING:",
    "RECORD_SEPARATOR:",
    "COLUMN_SEPARATOR:",
    "ESC_CHARACTER:",
    "COLUMNS:",
    "SEVERITY_MAP:",
    "HEADER_END",
)

TIMESTAMP_REGEX = re.compile(r"(\d{4}[/-]\d{2}[/-]\d{2}[\sT]\d{2}:\d{2}:\d{2}(?:[.,]\d{1,6})?)")


class LogService:
    """
    Service for inspecting local SAP BusinessObjects server trace logs (.glf, .log, .trc).
    Designed for co-located execution on the SAP BO host (Linux or Windows).
    """

    CHUNK_SIZE = 65536  # 64 KB streaming chunks

    def __init__(self, log_dir: Optional[str | Path] = None):
        self._explicit_log_dir = Path(log_dir) if log_dir else None

    def _get_log_dir(self) -> Path:
        """
        Resolves and validates the SAP BusinessObjects logging directory.
        Checks explicit constructor path, SAP_BO_LOG_DIR environment variable,
        and standard Linux/Windows installation paths.
        """
        raw_path = self._explicit_log_dir or (
            Path(os.environ["SAP_BO_LOG_DIR"]) if os.getenv("SAP_BO_LOG_DIR") else None
        )
        if raw_path is not None:
            resolved = raw_path.expanduser().resolve()
            if not resolved.exists() or not resolved.is_dir():
                raise BOELogError(
                    f"Configured SAP_BO_LOG_DIR '{raw_path}' does not exist or is not a directory. "
                    "Verify the path on the SAP BusinessObjects host."
                )
            return resolved

        for candidate_str in (*DEFAULT_LINUX_LOG_DIRS, *DEFAULT_WINDOWS_LOG_DIRS):
            candidate = Path(candidate_str)
            if candidate.exists() and candidate.is_dir():
                return candidate.resolve()

        raise BOELogError(
            "SAP BusinessObjects log directory is not configured. "
            "Set SAP_BO_LOG_DIR in your .env or service environment "
            "(e.g. '/opt/bobj/sap_bobj/logging' on Linux or "
            r"'C:\Program Files (x86)\SAP BusinessObjects\SAP BusinessObjects Enterprise XI 4.0\logging' on Windows)."
        )

    def _resolve_safe_file(self, file_name: str) -> Path:
        """
        Resolves a relative log file name strictly within SAP_BO_LOG_DIR.
        Blocks any path traversal ('../', absolute outside paths, or escaping symlinks).
        """
        base_dir = self._get_log_dir()
        if not file_name or not file_name.strip():
            raise BOELogError("Log file name cannot be empty.")

        candidate = (base_dir / file_name).resolve()
        if not candidate.is_relative_to(base_dir):
            raise BOELogError(f"Security violation: Requested path '{file_name}' escapes the sandboxed SAP_BO_LOG_DIR.")
        if not candidate.exists() or not candidate.is_file():
            raise BOELogError(f"Log file '{file_name}' not found inside '{base_dir}'.")
        return candidate

    @staticmethod
    def _infer_server_type(file_name: str) -> str:
        """Infers the SAP BO server component from a log file name."""
        lower = file_name.lower()
        if "webi" in lower or "wireportserver" in lower:
            return "WebiProcessingServer"
        if "jobserver" in lower or "adaptivejob" in lower or "ajs" in lower:
            return "AdaptiveJobServer"
        if "aps" in lower or "adaptiveprocessing" in lower:
            return "AdaptiveProcessingServer"
        if "cms" in lower:
            return "CentralManagementServer"
        if "wacs" in lower or "tomcat" in lower or "biprws" in lower:
            return "WACS/Tomcat"
        if "connectionserver" in lower or "cs_" in lower:
            return "ConnectionServer"
        if " eventserver" in lower or "fileserver" in lower or "frs" in lower:
            return "FileRepositoryServer"
        return "Other"

    @classmethod
    def _iter_lines_reverse(
        cls,
        file_path: Path,
        discard_incomplete_tail: bool = True,
    ) -> Iterator[Tuple[int, str]]:
        """
        Streams lines from a log file in reverse order (newest first) using fixed 64 KB chunks.
        Returns (1-based line_number, cleaned_line_text).
        Handles concurrent writes safely by discarding an unterminated trailing line if present.
        """
        with open(file_path, "rb") as f:
            f.seek(0, os.SEEK_END)
            file_size = f.tell()
            if file_size == 0:
                return

            # Count total newline characters in streaming chunks to maintain accurate 1-based line numbers
            total_newlines = 0
            f.seek(0)
            while chunk := f.read(cls.CHUNK_SIZE):
                total_newlines += chunk.count(b"\n")

            pos = file_size
            remainder = b""
            first_chunk = True
            current_line_no = total_newlines + 1

            while pos > 0:
                read_size = min(cls.CHUNK_SIZE, pos)
                pos -= read_size
                f.seek(pos)
                data = f.read(read_size) + remainder
                parts = data.split(b"\n")

                if first_chunk:
                    first_chunk = False
                    # If the file ends with \n, the last element is empty b""
                    if parts[-1] == b"":
                        parts.pop()
                        current_line_no = total_newlines
                    elif discard_incomplete_tail and pos > 0:
                        # Discard trailing partial line actively being written by SAP BO
                        parts.pop()
                        current_line_no = total_newlines

                remainder = parts[0]
                for raw_line in reversed(parts[1:]):
                    text = raw_line.decode("utf-8", errors="replace").rstrip("\r\x1e")
                    yield current_line_no, text
                    current_line_no -= 1

            if remainder:
                text = remainder.decode("utf-8", errors="replace").rstrip("\r\x1e")
                yield current_line_no, text

    @staticmethod
    def _parse_log_line(raw_line: str, fallback_server: str) -> Optional[Dict[str, Any]]:
        """
        Parses a single SAP BusinessObjects .glf (pipe-delimited) or .log/.trc line.
        Returns None for .glf metadata header lines or blank lines.
        """
        stripped = raw_line.strip()
        if not stripped or any(stripped.startswith(prefix) for prefix in GLF_HEADER_PREFIXES):
            return None

        # Pipe-delimited SAP BO .glf trace format
        if "|" in stripped:
            cols = [c.strip() for c in stripped.split("|")]
            # Standard 34-column SAP BO 4.x GLF record
            if len(cols) >= 12:
                timestamp_str = cols[2] if len(cols) > 2 else ""
                raw_sev = cols[5] if len(cols) > 5 else "I"
                device_name = cols[7] if len(cols) > 7 and cols[7] else fallback_server
                thread_id = cols[9] if len(cols) > 9 else ""
                user_name = cols[27] if len(cols) > 27 else ""
                message = cols[-1]
                return {
                    "timestamp": timestamp_str,
                    "severity": SEVERITY_NORMALIZATION.get(raw_sev.upper(), raw_sev or "Info"),
                    "server_name": device_name,
                    "thread_id": thread_id,
                    "user": user_name,
                    "message": message,
                }
            # Compact pipe-delimited record (e.g., Time|Severity|DeviceName|ThreadID|Message)
            if len(cols) >= 4:
                timestamp_str = cols[0]
                raw_sev = cols[1]
                device_name = cols[2] or fallback_server
                thread_id = cols[3] if len(cols) > 4 else ""
                message = cols[-1]
                return {
                    "timestamp": timestamp_str,
                    "severity": SEVERITY_NORMALIZATION.get(raw_sev.upper(), raw_sev or "Info"),
                    "server_name": device_name,
                    "thread_id": thread_id,
                    "user": "",
                    "message": message,
                }

        # Standard text .log / .trc format
        ts_match = TIMESTAMP_REGEX.search(stripped)
        timestamp_str = ts_match.group(1) if ts_match else ""
        severity = "Info"
        upper = stripped.upper()
        if "FATAL" in upper:
            severity = "Fatal"
        elif "ERROR" in upper or "EXCEPTION" in upper or "SEVERE" in upper:
            severity = "Error"
        elif "WARN" in upper:
            severity = "Warning"

        return {
            "timestamp": timestamp_str,
            "severity": severity,
            "server_name": fallback_server,
            "thread_id": "",
            "user": "",
            "message": stripped,
        }

    # =========================================================================
    # Public Service API
    # =========================================================================

    def list_log_files(
        self,
        server_type: Optional[str] = None,
        hours_back: int = 24,
        max_files: int = 100,
    ) -> Dict[str, Any]:
        """
        Lists recent SAP BusinessObjects log files (.glf, .log, .trc) in SAP_BO_LOG_DIR,
        ordered by last modification timestamp (newest first).
        """
        base_dir = self._get_log_dir()
        cutoff_ts = (datetime.now(timezone.utc) - timedelta(hours=max(1, hours_back))).timestamp()
        server_filter = server_type.strip().lower() if server_type else None

        entries: List[Dict[str, Any]] = []
        for path in base_dir.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_LOG_EXTENSIONS:
                continue
            try:
                stat = path.stat()
            except OSError:
                continue

            if stat.st_mtime < cutoff_ts:
                continue

            rel_name = path.relative_to(base_dir).as_posix()
            inferred_server = self._infer_server_type(path.name)
            if (
                server_filter
                and server_filter not in inferred_server.lower()
                and server_filter not in path.name.lower()
            ):
                continue

            entries.append(
                {
                    "file_name": rel_name,
                    "server_type": inferred_server,
                    "size_bytes": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                    "_mtime": stat.st_mtime,
                }
            )

        entries.sort(key=lambda x: x["_mtime"], reverse=True)
        truncated = len(entries) > max_files
        selected = entries[:max_files]
        for item in selected:
            item.pop("_mtime", None)

        return {
            "log_dir": str(base_dir),
            "hours_back": hours_back,
            "server_type_filter": server_type,
            "total_matching_files": len(entries),
            "is_truncated": truncated,
            "files": selected,
        }

    def search_logs(
        self,
        pattern: str,
        server_type: Optional[str] = None,
        hours_back: int = 12,
        severity: Optional[str] = None,
        max_matches: int = 50,
    ) -> Dict[str, Any]:
        """
        Streams and searches recent SAP BusinessObjects log files for an error code, CUID, DocID, or regex pattern.
        Scans newest files and newest lines first.
        """
        if not pattern or not pattern.strip():
            raise BOELogError("Search pattern cannot be empty.")

        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            regex = re.compile(re.escape(pattern), re.IGNORECASE)

        norm_severity = SEVERITY_NORMALIZATION.get(severity.strip().upper(), severity.strip()) if severity else None
        file_listing = self.list_log_files(server_type=server_type, hours_back=hours_back, max_files=50)
        base_dir = Path(file_listing["log_dir"])

        matches: List[Dict[str, Any]] = []
        files_scanned = 0

        for file_meta in file_listing["files"]:
            if len(matches) >= max_matches:
                break

            file_path = base_dir / file_meta["file_name"]
            fallback_server = file_meta["server_type"]
            files_scanned += 1

            try:
                for line_no, raw_line in self._iter_lines_reverse(file_path, discard_incomplete_tail=False):
                    parsed = self._parse_log_line(raw_line, fallback_server=fallback_server)
                    if parsed is None:
                        continue

                    if norm_severity and parsed["severity"].lower() != norm_severity.lower():
                        continue

                    if regex.search(raw_line) or regex.search(parsed["message"]):
                        matches.append(
                            {
                                "file_name": file_meta["file_name"],
                                "line_number": line_no,
                                "timestamp": parsed["timestamp"],
                                "severity": parsed["severity"],
                                "server_name": parsed["server_name"],
                                "thread_id": parsed["thread_id"],
                                "user": parsed["user"],
                                "message": parsed["message"],
                            }
                        )
                        if len(matches) >= max_matches:
                            break
            except OSError as e:
                logger.warning(f"Skipping unreadable log file '{file_path}': {e}")

        return {
            "log_dir": str(base_dir),
            "pattern": pattern,
            "server_type_filter": server_type,
            "severity_filter": norm_severity,
            "hours_back": hours_back,
            "files_scanned": files_scanned,
            "matches_returned": len(matches),
            "max_matches": max_matches,
            "matches": matches,
        }

    def get_log_context(
        self,
        file_name: str,
        line_number: int,
        context_lines: int = 20,
    ) -> Dict[str, Any]:
        """
        Retrieves surrounding lines around a specific 1-based line_number in a SAP BO log file.
        Ideal for inspecting full stack traces or preceding query parameters around an error.
        """
        file_path = self._resolve_safe_file(file_name)
        if line_number < 1:
            raise BOELogError("line_number must be >= 1.")

        radius = max(1, min(context_lines, 200))
        start_line = max(1, line_number - radius)
        end_line = line_number + radius

        collected: List[Dict[str, Any]] = []
        fallback_server = self._infer_server_type(file_path.name)

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                for idx, raw_line in enumerate(f, start=1):
                    if idx < start_line:
                        continue
                    if idx > end_line:
                        break
                    cleaned = raw_line.rstrip("\r\n\x1e")
                    parsed = self._parse_log_line(cleaned, fallback_server=fallback_server)
                    collected.append(
                        {
                            "line_number": idx,
                            "is_target_line": idx == line_number,
                            "timestamp": parsed["timestamp"] if parsed else "",
                            "severity": parsed["severity"] if parsed else "Header",
                            "message": parsed["message"] if parsed else cleaned,
                            "raw": cleaned,
                        }
                    )
        except OSError as e:
            raise BOELogError(f"Failed to read log file '{file_name}': {e}") from e

        return {
            "file_name": file_name,
            "target_line": line_number,
            "start_line": start_line,
            "end_line": end_line,
            "lines_returned": len(collected),
            "context": collected,
        }
