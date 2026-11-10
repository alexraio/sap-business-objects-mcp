"""
Unit tests for Local SAP BusinessObjects Server Log Analysis Service (LogService).
Tests path sandboxing, reverse-chunked .glf/.log streaming, severity filtering, and context extraction.
"""

from pathlib import Path

import pytest

from core.exceptions import BOELogError
from services.log_service import LogService

SAMPLE_GLF_CONTENT = """FILE_TYPE:DAAA96DE-B0FB-4c6e-AF7B-A445F5BF9BE2
ENCODING:UTF8
RECORD_SEPARATOR:30
COLUMN_SEPARATOR:124
COLUMNS:Location|Guid|Time|Tzone|Trace|Log|Importance|Severity|Exception|DeviceName|ProcessID|ThreadID|ThreadName|ScopeTag|MajorTick|MinorTick|MajorDepth|MinorDepth|RootName|RootID|CallerName|CallerID|CalleeName|CalleeID|ActionID|DSRRootContextID|DSRTransaction|DSRConnection|DSRCounter|User|ArchitectComponent|DeveloperComponent|Administrator|Unit|CSNComponent|Text
HEADER_END
src/webi.cpp:101|guid-1|2026/11/09 02:10:00.100|+0100| | |1|I| |webiserver_BO43.WebIntelligenceProcessingServer|1234|401|Worker1| |0|0|0|0| | | | | | | | | | | |alice|Webi|Engine| | | |Opening document ID 14820\x1e
src/webi.cpp:205|guid-2|2026/11/09 02:10:05.250|+0100|Error| |1|E|X|webiserver_BO43.WebIntelligenceProcessingServer|1234|401|Worker1| |0|0|0|0| | | | | | | | | | | |alice|Webi|Engine| | | |Database error: ORA-01017: invalid username/password; logon denied. (IES 10901)\x1e
src/webi.cpp:310|guid-3|2026/11/09 02:11:12.900|+0100| |Fatal|1| |X|webiserver_BO43.WebIntelligenceProcessingServer|1234|402|Worker2| |0|0|0|0| | | | | | | | | | | |Administrator|Webi|Engine| | | |Corba exception while refreshing DP0 (WIS 30553)\x1e
"""


@pytest.fixture
def log_dir_fixture(tmp_path: Path) -> Path:
    webi_log = tmp_path / "webiserver_BO43_trace.000001.glf"
    webi_log.write_text(SAMPLE_GLF_CONTENT, encoding="utf-8")

    ajs_log = tmp_path / "AdaptiveJobServer_20261109.log"
    ajs_log.write_text(
        "2026-11-09 03:00:01.000 INFO Starting job instance 99201\n"
        "2026-11-09 03:00:15.500 ERROR Publication bursting failed with code FBE60502\n",
        encoding="utf-8",
    )
    return tmp_path


class TestLogService:
    def test_unconfigured_log_dir_raises(self, monkeypatch):
        monkeypatch.delenv("SAP_BO_LOG_DIR", raising=False)
        svc = LogService(log_dir=Path("/nonexistent/bo/logging/path"))
        with pytest.raises(BOELogError, match="does not exist"):
            svc.list_log_files()

    def test_path_traversal_blocked(self, log_dir_fixture: Path):
        svc = LogService(log_dir=log_dir_fixture)
        with pytest.raises(BOELogError, match="Security violation"):
            svc.get_log_context("../outside.log", line_number=1)

    def test_list_log_files_and_filtering(self, log_dir_fixture: Path):
        svc = LogService(log_dir=log_dir_fixture)
        res = svc.list_log_files(hours_back=24)
        assert res["total_matching_files"] == 2
        server_types = {f["server_type"] for f in res["files"]}
        assert "WebiProcessingServer" in server_types
        assert "AdaptiveJobServer" in server_types

        webi_only = svc.list_log_files(server_type="WebiProcessingServer", hours_back=24)
        assert webi_only["total_matching_files"] == 1
        assert webi_only["files"][0]["file_name"] == "webiserver_BO43_trace.000001.glf"

    def test_search_glf_logs_reverse_order_and_severity(self, log_dir_fixture: Path):
        svc = LogService(log_dir=log_dir_fixture)

        # Search for IES 10901 in Webi logs
        res = svc.search_logs(pattern="IES 10901", server_type="Webi", hours_back=24)
        assert res["matches_returned"] == 1
        match = res["matches"][0]
        assert match["severity"] == "Error"
        assert match["user"] == "alice"
        assert "ORA-01017" in match["message"]
        assert match["line_number"] == 8

        # Filter by Fatal severity
        fatal_res = svc.search_logs(pattern="WIS 30553", severity="Fatal", hours_back=24)
        assert fatal_res["matches_returned"] == 1
        assert fatal_res["matches"][0]["severity"] == "Fatal"

        # Filter mismatch returns 0
        none_res = svc.search_logs(pattern="WIS 30553", severity="Info", hours_back=24)
        assert none_res["matches_returned"] == 0

    def test_get_log_context_window(self, log_dir_fixture: Path):
        svc = LogService(log_dir=log_dir_fixture)
        ctx = svc.get_log_context("webiserver_BO43_trace.000001.glf", line_number=8, context_lines=1)
        assert ctx["target_line"] == 8
        assert ctx["lines_returned"] == 3
        target_entries = [c for c in ctx["context"] if c["is_target_line"]]
        assert len(target_entries) == 1
        assert "IES 10901" in target_entries[0]["message"]


class TestRealGlfRecords:
    """Regression tests using verbatim records captured from a live SAP BO 4.3 APS log."""

    ERROR_LINE = (
        "|265C25AD74594147BC372A415C660D4C1542a|2026 04 17 11:04:32.337|+0200|Error| |>>|E| "
        "|aps_orarhel01.AdaptiveProcessingServer| 3178|1806|server-shutdown | ||||||||||||||||||||"
        "com.sap.businessobjects.analyticshub.framework.system.helper.CommonHelper||"
        "AnalyticsHub Framework - executeWithFileLock() - Error while closing the lockfile"
    )
    FATAL_LINE = (
        "|265C25AD74594147BC372A415C660D4C1542b|2026 04 17 11:04:32.337|+0200| |Fatal|  | | "
        "|aps_orarhel01.AdaptiveProcessingServer| 3178|1806|server-shutdown | |0|0|0|0|"
        "BIPSDK.InfoStore:query|ora-rhel-01:3178:1806.12088:1|-|-|BIPSDK.InfoStore:query|"
        "ora-rhel-01:3178:1806.12088:1|ClJR8bXO.EcppBpg_f_vDkk2ba3|||||||||"
        "com.crystaldecisions.enterprise.ocaframework.ManagedService||invoke(): the service is dead "
    )

    def test_error_record_fields(self):
        rec = LogService._parse_log_line(self.ERROR_LINE, "fallback")
        assert rec["severity"] == "Error"
        assert rec["server_name"] == "aps_orarhel01.AdaptiveProcessingServer"
        assert rec["thread_id"] == "server-shutdown"
        assert rec["timestamp"] == "2026 04 17 11:04:32.337"
        assert rec["message"].startswith("AnalyticsHub Framework")

    def test_fatal_record_uses_log_column(self):
        rec = LogService._parse_log_line(self.FATAL_LINE, "fallback")
        assert rec["severity"] == "Fatal"
        assert rec["message"].startswith("invoke(): the service is dead")
