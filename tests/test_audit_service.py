"""
Unit tests for SAP BusinessObjects Auditing Database Direct ODBC Service (AuditService).
Tests read-only SQL validation guardrails, connection string construction, row truncation, and ADS_EVENT queries.
"""

import datetime as dt
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from core.exceptions import BOEAuditDBError
from services.audit_service import AuditDBConfig, AuditService


class TestAuditSQLValidator:
    @pytest.mark.parametrize(
        "valid_sql",
        [
            "SELECT Event_ID, User_Name FROM ADS_EVENT",
            "  select count(*) from ADS_EVENT where Status_ID <> 0; ",
            "-- Leading comment\nWITH recent AS (SELECT * FROM ADS_EVENT) SELECT * FROM recent",
            "/* Block comment */ SELECT Object_Name FROM ADS_EVENT WHERE Object_Name = 'Drop;Update;Delete'",
        ],
    )
    def test_validate_readonly_sql_allows_valid_selects(self, valid_sql: str):
        cleaned = AuditService.validate_readonly_sql(valid_sql)
        assert cleaned.upper().startswith(("SELECT", "WITH"))

    @pytest.mark.parametrize(
        "malicious_sql",
        [
            "",
            "   -- only a comment",
            "DELETE FROM ADS_EVENT WHERE 1=1",
            "UPDATE ADS_EVENT SET User_Name = 'hacked'",
            "DROP TABLE ADS_EVENT",
            "INSERT INTO ADS_EVENT VALUES (1)",
            "SELECT * FROM ADS_EVENT; DROP TABLE ADS_EVENT",
            "SELECT * INTO new_table FROM ADS_EVENT",
            "EXEC sp_configure",
            "TRUNCATE TABLE ADS_EVENT",
        ],
    )
    def test_validate_readonly_sql_blocks_mutations_and_multi_statements(self, malicious_sql: str):
        with pytest.raises(BOEAuditDBError):
            AuditService.validate_readonly_sql(malicious_sql)


class TestAuditDBConfig:
    def test_build_connection_string_from_dsn(self):
        cfg = AuditDBConfig(
            dsn="BI4_Audit_DSN_1651343769",
            user="dba",
            password=SecretStr("secret_pwd"),
        )
        conn_str = cfg.build_connection_string()
        assert conn_str == "DSN=BI4_Audit_DSN_1651343769;UID=dba;PWD=secret_pwd"

    def test_build_connection_string_from_driver_and_host(self):
        cfg = AuditDBConfig(
            driver="SQL Anywhere 17",
            host="ora-rhel-01.lab.pf.box",
            port=2638,
            database="BI4_Audit",
            server_name="BI4_1651343769",
            user="dba",
            password=SecretStr("secret_pwd"),
        )
        conn_str = cfg.build_connection_string()
        assert "Driver={SQL Anywhere 17}" in conn_str
        assert "ENG=BI4_1651343769" in conn_str
        assert "LINKS=tcpip(host=ora-rhel-01.lab.pf.box;port=2638)" in conn_str

    def test_unconfigured_raises(self):
        cfg = AuditDBConfig()
        with pytest.raises(BOEAuditDBError, match="not configured"):
            cfg.build_connection_string()


class TestAuditServiceExecution:
    @patch("services.audit_service.pyodbc")
    def test_execute_query_with_row_capping_and_serialization(self, mock_pyodbc):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pyodbc.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        mock_cursor.description = [("Event_ID",), ("Start_Time",), ("Duration_ms",)]
        # Return 3 rows when max_rows=2 to trigger is_truncated=True
        mock_cursor.fetchmany.return_value = [
            (101, dt.datetime(2026, 11, 9, 8, 30, 0), Decimal("1450.5")),
            (102, dt.datetime(2026, 11, 9, 8, 31, 0), Decimal("820.0")),
            (103, dt.datetime(2026, 11, 9, 8, 32, 0), Decimal("300.0")),
        ]

        cfg = AuditDBConfig(dsn="BI4_Audit_DSN", user="dba", password=SecretStr("pwd"))
        svc = AuditService(config=cfg)
        res = svc.execute_query("SELECT Event_ID, Start_Time, Duration_ms FROM ADS_EVENT", max_rows=2)

        mock_pyodbc.connect.assert_called_once_with("DSN=BI4_Audit_DSN;UID=dba;PWD=pwd", readonly=True, timeout=20)
        mock_cursor.fetchmany.assert_called_once_with(3)
        assert res["rows_returned"] == 2
        assert res["is_truncated"] is True
        assert res["rows"][0]["Event_ID"] == 101
        assert res["rows"][0]["Start_Time"] == "2026-11-09T08:30:00"
        assert res["rows"][0]["Duration_ms"] == 1450.5

    @patch("services.audit_service.pyodbc")
    def test_high_level_audit_methods(self, mock_pyodbc):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pyodbc.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.description = [("Event_ID",), ("Object_Name",), ("Error_Code",)]
        mock_cursor.fetchmany.return_value = [(5001, "Financial_Summary.wid", "IES 10901")]

        svc = AuditService(config=AuditDBConfig(dsn="BI4_Audit_DSN"))

        failed = svc.get_failed_events(hours_back=12, event_type_id=1003)
        assert failed["rows_returned"] == 1
        assert failed["event_type_id"] == 1003

        heavy = svc.get_heavy_reports(days_back=7, top_n=10)
        assert heavy["days_back"] == 7

        activity = svc.get_user_activity(username="alice", hours_back=24)
        assert activity["username_filter"] == "alice"
