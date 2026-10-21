"""
Unit tests for DiagnosticService and Pydantic diagnostic contracts.
Validates normalization, error signatures, clustering, multi-cause ranking, and edge cases.
"""

from unittest.mock import MagicMock

from core.models import BatchDiagnosticsReport, FailureCategory
from services.diagnostic_service import DiagnosticService


class TestDiagnosticServiceSignatures:
    """Tests for regex-based error signature normalization."""

    def test_extract_signature_deadlock(self, diagnostic_service: DiagnosticService):
        raw = "2026-10-21 03:15:22 [PID 1245] ORA-00060: deadlock detected while waiting for resource on 10.0.1.42"
        sig = diagnostic_service.extract_error_signature(raw)
        assert "DB_LOCK_DEADLOCK" in sig
        assert "ORA-00060" in sig

    def test_extract_signature_auth_failure(self, diagnostic_service: DiagnosticService):
        raw = "Connection to DWH failed: ORA-01017: invalid username/password; logon denied"
        sig = diagnostic_service.extract_error_signature(raw)
        assert "DB_AUTH_FAILURE" in sig

    def test_extract_signature_network_timeout(self, diagnostic_service: DiagnosticService):
        raw = "java.net.SocketTimeoutException: Read timed out after 120000 ms to host dbprod.corp:1521"
        sig = diagnostic_service.extract_error_signature(raw)
        assert "NETWORK_TIMEOUT" in sig

    def test_extract_signature_wis_30553(self, diagnostic_service: DiagnosticService):
        raw = "An internal error occurred while calling 'processDPCommandsEx' API. (Error: WIS 30553)"
        sig = diagnostic_service.extract_error_signature(raw)
        assert "WIS 30553" in sig
        assert "Data Provider" in sig

    def test_extract_signature_publication_fbe(self, diagnostic_service: DiagnosticService):
        raw = "An exception was caught while scheduling the publication. (FBE60502)"
        sig = diagnostic_service.extract_error_signature(raw)
        assert "FBE60502" in sig
        assert "Publishing Service" in sig

    def test_extract_signature_server_oom(self, diagnostic_service: DiagnosticService):
        raw = "java.lang.OutOfMemoryError: Java heap space during PDF rendering"
        sig = diagnostic_service.extract_error_signature(raw)
        assert "SERVER_OOM" in sig

    def test_extract_signature_empty_fallback(self, diagnostic_service: DiagnosticService):
        sig = diagnostic_service.extract_error_signature(None, "")
        assert "UNKNOWN_ABRUPT_SERVER_TERMINATION" in sig


class TestMultiCauseRanking:
    """Tests for the ranked 3-cause recommendation engine."""

    def test_deadlock_ranking_structure(self, diagnostic_service: DiagnosticService):
        causes = diagnostic_service.classify_and_rank_causes(
            error_signature="DB_LOCK_DEADLOCK: Rilevato blocco transazionale",
            sample_status_info="ORA-00060: deadlock detected",
        )
        assert len(causes) <= 3
        assert len(causes) >= 1
        assert causes[0].rank == 1
        assert causes[0].category == FailureCategory.DB_LOCK_CONCURRENCY
        assert causes[0].probability_score >= 0.7
        assert len(causes[0].recommended_actions) >= 1

        # Check descending scores
        scores = [c.probability_score for c in causes]
        assert scores == sorted(scores, reverse=True)

    def test_missing_prompts_ranking(self, diagnostic_service: DiagnosticService):
        causes = diagnostic_service.classify_and_rank_causes(
            error_signature="Valore prompt mancante",
            sample_status_info="WIS 30270 mandatory parameter missing",
            missing_prompts=["Codice_Regione", "Anno_Fiscale"],
        )
        assert causes[0].category == FailureCategory.MISSING_PROMPTS
        assert "Codice_Regione" in causes[0].technical_explanation
        assert causes[0].probability_score > 0.8

    def test_wis30553_cache_corruption_ranking(self, diagnostic_service: DiagnosticService):
        causes = diagnostic_service.classify_and_rank_causes(
            error_signature="WIS 30553: Errore di elaborazione Data Provider",
            sample_status_info="processDPCommandsEx",
        )
        assert causes[0].category == FailureCategory.CACHE_CORRUPTED
        assert any("purga" in act.lower() for act in causes[0].recommended_actions)


class TestDiagnosticBatchOrchestration:
    """Tests for scan, clustering and full report orchestration."""

    def test_clean_night_zero_failures(self, diagnostic_service: DiagnosticService, mock_client: MagicMock):
        mock_client.post.return_value = {"entries": []}
        report = diagnostic_service.diagnose_batch(hours_back=12)

        assert isinstance(report, BatchDiagnosticsReport)
        assert report.total_failed_instances == 0
        assert report.clusters_count == 0
        assert len(report.clusters) == 0
        assert "successo" in report.executive_summary.lower()

    def test_batch_clustering_and_deduplication(self, diagnostic_service: DiagnosticService, mock_client: MagicMock):
        mock_client.post.return_value = {
            "entries": [
                {
                    "SI_ID": 1001,
                    "SI_NAME": "Sales_North",
                    "SI_PARENTID": 500,
                    "SI_STATUSINFO": "2026-10-21 ORA-00060: deadlock detected on PID 44",
                },
                {
                    "SI_ID": 1002,
                    "SI_NAME": "Sales_South",
                    "SI_PARENTID": 501,
                    "SI_STATUSINFO": "2026-10-21 ORA-00060: deadlock detected on PID 49",
                },
                {
                    "SI_ID": 1003,
                    "SI_NAME": "Sales_East",
                    "SI_PARENTID": 502,
                    "SI_STATUSINFO": "2026-10-21 ORA-00060: deadlock detected on PID 52",
                },
                {
                    "SI_ID": 1004,
                    "SI_NAME": "Monthly_Financials",
                    "SI_PARENTID": 600,
                    "SI_STATUSINFO": "Error: WIS 30553 calling processDPCommandsEx",
                },
            ]
        }

        report = diagnostic_service.diagnose_batch(hours_back=12, kind="Webi")
        assert report.total_failed_instances == 4
        assert report.clusters_count == 2  # Deadlocks clustered together, WIS 30553 separate

        # Primary cluster should be the deadlock cluster with 3 instances
        primary_cluster = report.clusters[0]
        assert primary_cluster.affected_count == 3
        assert "Sales_North" in primary_cluster.sample_report_names
        assert primary_cluster.top_causes[0].category == FailureCategory.DB_LOCK_CONCURRENCY

        # Secondary cluster should have 1 instance
        secondary_cluster = report.clusters[1]
        assert secondary_cluster.affected_count == 1
        assert secondary_cluster.top_causes[0].category == FailureCategory.CACHE_CORRUPTED

    def test_smart_enrichment_orphan_document_graceful(
        self, diagnostic_service: DiagnosticService, mock_client: MagicMock
    ):
        # When parent document returns error / 404
        mock_client.get.side_effect = Exception("HTTP 404 Not Found")
        enrichment = diagnostic_service.smart_enrichment("99999")
        assert enrichment == {"missing_prompts": []}

    def test_scan_query_kind_and_folder_filtering(self, diagnostic_service: DiagnosticService, mock_client: MagicMock):
        mock_client.post.return_value = {"entries": []}
        diagnostic_service.scan_failed_instances(hours_back=6, kind="Publication", folder_id="777")

        called_query = mock_client.post.call_args[1]["json_data"]["query"]
        assert "SI_KIND = 'Publication'" in called_query
        assert "SI_PARENTID = 777" in called_query
        assert "SI_SCHEDULE_STATUS = 3" in called_query

    def test_scan_failed_instances_network_error(self, diagnostic_service: DiagnosticService, mock_client: MagicMock):
        mock_client.post.side_effect = Exception("CMS network timeout")
        entries = diagnostic_service.scan_failed_instances(hours_back=12)
        assert entries == []

    def test_publication_bursting_ranking(self, diagnostic_service: DiagnosticService):
        causes = diagnostic_service.classify_and_rank_causes(
            error_signature="FBE60502: Errore del motore di Pubblicazione",
            sample_status_info="FBE60502 Publication scope failure",
        )
        assert causes[0].category == FailureCategory.BURSTING_RECIPIENT
        assert causes[1].category == FailureCategory.SERVER_RESOURCE_OOM

    def test_network_timeout_ranking(self, diagnostic_service: DiagnosticService):
        causes = diagnostic_service.classify_and_rank_causes(
            error_signature="NETWORK_TIMEOUT: Connessione di rete o socket timeout",
            sample_status_info="SocketTimeoutException",
        )
        assert causes[0].category == FailureCategory.NETWORK_TIMEOUT

    def test_generic_unknown_ranking(self, diagnostic_service: DiagnosticService):
        causes = diagnostic_service.classify_and_rank_causes(
            error_signature="UNKNOWN_ABRUPT_SERVER_TERMINATION: SI_STATUSINFO vuoto",
            sample_status_info="",
        )
        assert causes[0].category == FailureCategory.SERVER_RESOURCE_OOM
        assert causes[1].category == FailureCategory.NETWORK_TIMEOUT
        assert causes[2].category == FailureCategory.UNKNOWN_GENERIC

    def test_batch_truncation_flag_active(self, diagnostic_service: DiagnosticService, mock_client: MagicMock):
        mock_client.post.return_value = {
            "entries": [
                {"SI_ID": 1, "SI_NAME": "Rep1", "SI_STATUSINFO": "WIS 30553"},
                {"SI_ID": 2, "SI_NAME": "Rep2", "SI_STATUSINFO": "WIS 30553"},
            ]
        }
        report = diagnostic_service.diagnose_batch(hours_back=1, max_instances=2)
        assert report.is_truncated is True
        assert "ATTENZIONE" in report.executive_summary

    def test_smart_enrichment_finds_mandatory_prompts(
        self, diagnostic_service: DiagnosticService, mock_client: MagicMock
    ):
        mock_client.get.return_value = {
            "parameters": {
                "parameter": [
                    {
                        "@optional": "false",
                        "name": "Anno_Esercizio",
                        "answer": None,
                        "defaultValues": None,
                    },
                    {
                        "@optional": "true",
                        "name": "Note_Facoltative",
                        "answer": None,
                    },
                ]
            }
        }
        res = diagnostic_service.smart_enrichment("8888")
        assert res["missing_prompts"] == ["Anno_Esercizio"]
