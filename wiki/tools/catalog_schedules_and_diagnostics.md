---
type: tool_catalog
title: Schedules, Instances & Batch Diagnostics Tools Catalog
description: Reference of MCP tools for auditing report schedules, inspecting historical execution instances, and running automated batch failure Root Cause Analysis (RCA).
status: active
last_updated: 2026-11-06
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
