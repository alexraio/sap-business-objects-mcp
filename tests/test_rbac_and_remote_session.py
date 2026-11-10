"""
Unit tests for Multi-Tenant RBAC Enforcement, Remote Session Isolation, and Triple Diagnostic Correlation.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import server
from core.exceptions import BOEPermissionError
from core.session import SessionManager


class TestRBACAndRemoteSession:
    def test_admin_service_is_user_admin_builtin_administrator(self):
        client = MagicMock()
        from services.admin_service import AdminService

        admin_svc = AdminService(client)
        assert admin_svc.is_user_admin("Administrator") is True
        assert admin_svc.is_user_admin("administrator") is True
        # No CMS query needed for built-in Administrator
        client.post.assert_not_called()

    def test_admin_service_is_user_admin_group_membership(self):
        client = MagicMock()
        from services.admin_service import AdminService

        admin_svc = AdminService(client)
        with patch.object(
            admin_svc, "cms_query", return_value={"entries": [{"SI_ID": 1, "SI_NAME": "Administrators"}]}
        ):
            with patch.object(
                admin_svc,
                "get_group_users",
                return_value=[{"id": "42", "username": "bo_ops_lead", "description": ""}],
            ):
                assert admin_svc.is_user_admin("bo_ops_lead") is True
                assert admin_svc.is_user_admin("standard_analyst") is False

    def test_remote_mode_disables_default_credential_fallback(self):
        mock_provider = MagicMock()
        manager = SessionManager(credential_provider=mock_provider, remote_mode=True)

        session = manager.get_or_create_session("remote_client_1")
        assert session.credentials is None
        mock_provider.get_credentials.assert_not_called()

    def test_server_admin_tools_reject_non_admin_user(self):
        server.default_session.authenticated_user = "standard_analyst"
        server.default_session.is_admin = False

        try:
            with pytest.raises(RuntimeError, match="Access denied"):
                server.list_bo_logs.fn()

            with pytest.raises(RuntimeError, match="Access denied"):
                server.query_audit_db.fn(sql_query="SELECT COUNT(*) FROM ADS_EVENT")
        finally:
            server.default_session.authenticated_user = None
            server.default_session.is_admin = None

    def test_server_admin_tools_allow_administrator(self, tmp_path: Path):
        (tmp_path / "cms_trace.log").write_text("2026-11-09 04:00:00 ERROR CMS deadlock detected\n", encoding="utf-8")
        server.default_session.authenticated_user = "Administrator"
        server.default_session.is_admin = True

        try:
            with patch.object(server.parser.logs, "_explicit_log_dir", tmp_path):
                res = server.search_bo_logs.fn(pattern="deadlock", hours_back=24)
                assert res["matches_returned"] == 1
                assert "deadlock" in res["matches"][0]["message"]
        finally:
            server.default_session.authenticated_user = None
            server.default_session.is_admin = None

    def test_session_ensure_admin_raises_boe_permission_error(self):
        manager = SessionManager(remote_mode=True)
        session = manager.get_or_create_session("analyst_sess")
        session.authenticated_user = "analyst1"
        session.is_admin = False

        with pytest.raises(BOEPermissionError, match="Administrator privileges"):
            session.ensure_admin()

    def test_triple_correlation_in_diagnostic_service(self):
        client = MagicMock()
        mock_logs = MagicMock()
        mock_audit = MagicMock()

        mock_logs.search_logs.return_value = {
            "matches": [{"file_name": "webi.glf", "line_number": 44, "message": "ORA-01017 (IES 10901)"}]
        }
        mock_audit.get_failed_events.return_value = {
            "rows": [{"Event_ID": 9001, "Object_Name": "Sales_Report", "Error_Code": "IES 10901"}]
        }

        from services.diagnostic_service import DiagnosticService

        diag = DiagnosticService(client, log_service=mock_logs, audit_service=mock_audit)
        with patch.object(
            diag,
            "scan_failed_instances",
            return_value=[
                {
                    "SI_ID": 555,
                    "SI_NAME": "Sales_Report",
                    "SI_PARENTID": 100,
                    "SI_STATUSINFO": "Database error: ORA-01017 (IES 10901)",
                    "SI_ERROR_SEARCH_KEY": "IES 10901",
                }
            ],
        ):
            report = diag.diagnose_batch(hours_back=12, correlate_telemetry=True)
            assert report.clusters_count == 1
            cluster = report.clusters[0]
            assert len(cluster.correlated_log_entries) == 1
            assert cluster.correlated_log_entries[0]["file_name"] == "webi.glf"
            assert len(cluster.correlated_audit_events) == 1
            assert cluster.correlated_audit_events[0]["Event_ID"] == 9001

    @patch("core.self_diagnostics.requests.get")
    def test_get_mcp_server_diagnostics_masks_secrets_and_probes_subsystems(self, mock_get, tmp_path: Path):
        from core.self_diagnostics import sanitize_log_text

        masked = sanitize_log_text("DSN=BI4;UID=dba;PWD=SuperSecret123;X-SAP-LogonToken=TOKEN999")
        assert "SuperSecret123" not in masked
        assert "TOKEN999" not in masked
        assert "**********" in masked

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        with patch.object(server.parser.logs, "_explicit_log_dir", tmp_path):
            diag_report = server.get_mcp_server_diagnostics.fn(include_recent_logs=True, max_log_lines=10)
            assert "runtime" in diag_report
            assert "subsystems" in diag_report
            assert diag_report["subsystems"]["sap_bo_rest_api"]["reachable"] is True
            assert diag_report["subsystems"]["local_log_service"]["status"] == "ok"
            assert "recent_internal_logs" in diag_report


class TestIsolatedAuditProbe:
    """The auditing DB probe must never crash or freeze the host process (e.g. `doctor`)."""

    def test_unconfigured_probe_reports_error_without_crashing(self):
        from core.self_diagnostics import probe_audit_database

        with patch.dict("os.environ", {}, clear=False) as env:
            for key in ("SAP_BO_AUDIT_DSN", "SAP_BO_AUDIT_CONNECTION_STRING", "SAP_BO_AUDIT_DRIVER"):
                env.pop(key, None)
            probe = probe_audit_database(timeout_seconds=30)
        assert probe["connected"] is False
        assert probe["error"]

    def test_native_crash_is_reported_as_error(self):
        import core.self_diagnostics as diag

        with patch.object(
            diag,
            "_AUDIT_PROBE_SCRIPT",
            'import os; print(\'{"stage": "import", "pyodbc_installed": true}\', flush=True); os.abort()',
        ):
            probe = diag.probe_audit_database(timeout_seconds=30)
        assert probe["connected"] is False
        assert probe["pyodbc_installed"] is True
        assert "crashed" in probe["error"]

    def test_hang_is_reported_as_timeout(self):
        import core.self_diagnostics as diag

        with patch.object(diag, "_AUDIT_PROBE_SCRIPT", "import time; time.sleep(30)"):
            probe = diag.probe_audit_database(timeout_seconds=1)
        assert probe["connected"] is False
        assert "timed out" in probe["error"]
