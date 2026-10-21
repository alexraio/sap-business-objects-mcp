"""
Unit tests validating FastMCP server initialization, tool registration, and tool signatures.
"""

from unittest.mock import patch

import server


class TestServerToolRegistration:
    def test_total_registered_tools_count(self):
        """Verifies that all 47 enterprise MCP tools are properly registered on FastMCP."""
        tools = server.mcp._tool_manager._tools
        assert len(tools) == 47, f"Expected exactly 47 registered tools, got {len(tools)}"

    def test_essential_tools_present(self):
        tools = server.mcp._tool_manager._tools
        expected_tools = [
            # Auth
            "login",
            "logout",
            # Universes
            "get_universes",
            "get_universe_details",
            "get_universe_structure",
            "get_universe_related_reports",
            "get_universe_connection_id",
            # Webi Docs & Lifecycle
            "get_documents",
            "get_doc_details",
            "get_doc_properties",
            "save_webi_doc",
            "delete_webi_doc",
            # Prompts
            "get_doc_parameters",
            "get_parameter_lov",
            "refresh_webi_doc",
            # Tabs & Blocks
            "get_reports",
            "get_report_elements",
            "get_report_element_data",
            "get_variables",
            "get_comments",
            # Data Providers & SQL
            "get_dp",
            "get_dp_details",
            "get_dp_sql",
            "get_dp_specification",
            "refresh_dp",
            "purge_dp",
            "get_dp_mapping_proposal",
            "change_dp_datasource",
            # CMS Admin & Security
            "cms_query",
            "get_users",
            "get_user_details",
            "set_user_status",
            "get_user_groups",
            "get_group_users",
            "get_active_sessions",
            "terminate_session",
            # Schedules & Instances
            "get_doc_schedules",
            "get_doc_instances",
            "get_instance_details",
            "delete_instance",
            # InfoStore & Folders
            "get_folders",
            "get_folder_details",
            "create_folder",
            "delete_folder",
            "get_webi_docs",
            "get_categories",
            # Intelligent Diagnostics
            "diagnose_batch_failures",
        ]
        for t in expected_tools:
            assert t in tools, f"Missing tool in server: {t}"

    def test_tool_docstrings_populated(self):
        """Ensures that all tools have meaningful descriptive docstrings for LLM agents."""
        tools = server.mcp._tool_manager._tools
        for name, tool in tools.items():
            doc = getattr(tool.fn, "__doc__", "")
            assert doc and len(doc.strip()) > 10, f"Tool '{name}' lacks proper docstring documentation"

    @patch.object(server.parser, "set_logon_token")
    def test_login_tool_execution(self, mock_set_token):
        mock_set_token.return_value = "TOKEN_ABC"
        result = server.login.fn(username="test_admin", password="test_password")
        assert "Login successful for user 'test_admin'" in result
        mock_set_token.assert_called_once_with("test_admin", "test_password")

    @patch.object(server.parser, "bo_logoff")
    def test_logout_tool_execution(self, mock_logoff):
        mock_logoff.return_value = True
        result = server.logout.fn()
        assert "Logout successful" in result
        mock_logoff.assert_called_once()

    @patch.object(server.parser.diagnostic, "diagnose_batch")
    def test_diagnose_batch_failures_tool_execution(self, mock_diagnose):
        from core.models import BatchDiagnosticsReport

        mock_report = BatchDiagnosticsReport(
            scan_timestamp="2026-10-21T06:00:00Z",
            hours_back=12,
            kind="All",
            total_failed_instances=0,
            clusters_count=0,
            is_truncated=False,
            clusters=[],
            executive_summary="All batch executions completed successfully.",
        )
        mock_diagnose.return_value = mock_report

        res = server.diagnose_batch_failures.fn(hours_back=12, kind="All")
        assert isinstance(res, dict)
        assert res["total_failed_instances"] == 0
        assert res["clusters_count"] == 0
        assert "successfully" in res["executive_summary"]
        mock_diagnose.assert_called_once_with(hours_back=12, kind="All", folder_id=None, max_instances=100)
