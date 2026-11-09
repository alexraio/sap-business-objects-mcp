---
type: tool_catalog
title: Schedules, Instances & Batch Diagnostics Tools Catalog
description: Reference of MCP tools for auditing report schedules, inspecting historical execution instances, and running automated batch failure Root Cause Analysis (RCA).
status: active
last_updated: 2026-11-09
tags:
  - tools
  - schedules
  - instances
  - diagnostics
  - rca
related:
  - ./index.md
  - ../architecture/intelligent_diagnostics_engine.md
  - ../troubleshooting/index.md
---

# Schedules, Instances & Batch Diagnostics Tools Catalog

This catalog documents the MCP tools registered in [`server.py`](../../server.py) for schedule/instance lifecycle management (`services/schedule_service.py`) and automated batch failure diagnostics (`services/diagnostic_service.py`).

---

## 1. Schedules & Historical Instances Tools

| Tool Name | Tier | Signature | Description |
| :--- | :---: | :--- | :--- |
| `get_doc_schedules` | Tier 1 | `get_doc_schedules(webi_doc_id: str) -> List[Dict[str, Any]]` | Lists recurring schedule definitions, recurrence rules, and destination settings for a Webi document. |
| `get_doc_instances` | Tier 1 | `get_doc_instances(webi_doc_id: str, max_instances: int = 50) -> List[Dict[str, Any]]` | Lists historical execution instances (`SI_INSTANCE = 1`) with status (`Success`, `Failed`, `Running`) and timestamps. |
| `get_instance_details` | Tier 1 | `get_instance_details(instance_id: str) -> Dict[str, Any]` | Retrieves detailed execution telemetry and raw `SI_STATUSINFO` error messages for a specific instance ID. |
| `delete_instance` | **Tier 2** | `delete_instance(instance_id: str) -> str` | Deletes a historical execution instance from the CMS repository. **Requires confirmation.** |

---

## 2. Intelligent Batch Failure Diagnostics Tool

| Tool Name | Tier | Signature | Description |
| :--- | :---: | :--- | :--- |
| `diagnose_batch_failures` | Tier 1 | `diagnose_batch_failures(hours_back: int = 12, kind: str = "All", folder_id: Optional[str] = None, max_instances: int = 100) -> Dict[str, Any]` | Scans failed scheduled instances (`SI_SCHEDULE_STATUS = 3`) across Webi reports and Publications, normalizes error signatures, clusters failures via SHA-256, enriches parameter context, and returns a validated `BatchDiagnosticsReport` with up to 3 ranked probable causes and step-by-step remediation instructions per cluster. |

### Recommended Diagnostic Workflow
1. Run `diagnose_batch_failures(hours_back=24, kind="All")` to obtain the clustered executive summary.
2. For clusters requiring deeper inspection of a specific report's recurring schedule, call `get_doc_schedules(webi_doc_id)` or `get_instance_details(sample_instance_id)`.
3. Consult the corresponding runbook in [Troubleshooting & Error Runbooks](../troubleshooting/index.md) for the error code identified in `error_signature`.

---

## 3. Local SAP BO Server Log Inspection Tools (`LogService` — Admin-Only)

| Tool Name | Tier | Signature | Description |
| :--- | :---: | :--- | :--- |
| `list_bo_logs` | Tier 1 (Admin) | `list_bo_logs(server_type: Optional[str] = None, hours_back: int = 24, max_files: int = 100) -> Dict[str, Any]` | Lists recent `.glf`, `.log`, and `.trc` files in `SAP_BO_LOG_DIR` grouped by server component (`WebiProcessingServer`, `AdaptiveJobServer`, `CMS`, `WACS`). |
| `search_bo_logs` | Tier 1 (Admin) | `search_bo_logs(pattern: str, server_type: Optional[str] = None, hours_back: int = 12, severity: Optional[str] = None, max_matches: int = 50) -> Dict[str, Any]` | Streams and searches local `.glf`/`.log` files in reverse order (64 KB chunks from EOF) for error codes (`IES 10901`, `WIS 30553`, `ORA-01017`), CUIDs, or regex patterns. |
| `get_bo_log_context` | Tier 1 (Admin) | `get_bo_log_context(file_name: str, line_number: int, context_lines: int = 20) -> Dict[str, Any]` | Retrieves surrounding lines before and after a 1-based line number inside a local log file. |

---

## 4. Auditing Database ODBC Tools (`AuditService` — Admin-Only)

| Tool Name | Tier | Signature | Description |
| :--- | :---: | :--- | :--- |
| `get_audit_failed_events` | Tier 1 (Admin) | `get_audit_failed_events(hours_back: int = 24, event_type_id: Optional[int] = None, max_rows: int = 100) -> Dict[str, Any]` | Queries `ADS_EVENT` via `pyodbc` for failed platform events (`Status_ID <> 0` or populated `Error_Code`). |
| `get_audit_heavy_reports` | Tier 1 (Admin) | `get_audit_heavy_reports(days_back: int = 7, top_n: int = 20) -> Dict[str, Any]` | Identifies the slowest and heaviest reports in `ADS_EVENT` ranked by maximum and average execution duration (`Duration_ms`). |
| `get_audit_user_activity` | Tier 1 (Admin) | `get_audit_user_activity(username: Optional[str] = None, hours_back: int = 24, max_rows: int = 100) -> Dict[str, Any]` | Retrieves recent user logon, viewing, refresh, and export activity from `ADS_EVENT`. |
| `query_audit_db` | Tier 1 (Admin) | `query_audit_db(sql_query: str, max_rows: int = 200) -> Dict[str, Any]` | Executes a strictly read-only `SELECT` (or `WITH ... SELECT`) query against `ADS_*` tables using `cursor.fetchmany(max_rows)`. |

---

## 5. Remote MCP Server Self-Diagnostics Tool

| Tool Name | Tier | Signature | Description |
| :--- | :---: | :--- | :--- |
| `get_mcp_server_diagnostics` | Tier 1 | `get_mcp_server_diagnostics(include_recent_logs: bool = True, max_log_lines: int = 50) -> Dict[str, Any]` | Probes all 4 server subsystems (OS/Runtime & RBAC session state, `biprws` HTTP reachability, `SAP_BO_LOG_DIR` read access, `pyodbc` drivers & live Auditing DB ping) and returns sanitized internal `bo-mcp` logs from the in-memory ring buffer. |
