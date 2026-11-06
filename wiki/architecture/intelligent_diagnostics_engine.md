---
type: architecture
title: Intelligent Diagnostics Engine Architecture
description: Architectural specification of the automated batch failure Root Cause Analysis (RCA) engine, error signature clustering, and Pydantic v2 data contracts.
status: active
last_updated: 2026-11-06
tags:
  - diagnostics
  - rca
  - batch-failures
  - pydantic
related:
  - ./index.md
  - ./system_overview.md
  - ../tools/catalog_schedules_and_diagnostics.md
  - ../troubleshooting/index.md
  - ../sap_bo/connections_and_idt.md
---

# Intelligent Diagnostics Engine Architecture

The **Intelligent Diagnostics Engine** (`services/diagnostic_service.py`) automates Root Cause Analysis (RCA) for failed scheduled Web Intelligence reports and Publications (`SI_SCHEDULE_STATUS = 3`).

---

## 1. Architectural Rationale: 100% RESTful WACS vs. Direct CMS SQL

A critical architectural decision (**D2**) governs how `bo-mcp` inspects batch failures:

- **Why Direct SQL against the Physical CMS Database is Prohibited:**
  The underlying CMS relational database (Oracle, SQL Server, SAP HANA, DB2) stores `SI_SCHEDULEINFO`, prompt answers, destinations, and `SI_STATUSINFO` error payloads inside **proprietary compressed binary BLOBs** across tables like `CMS_INFOOBJECTS5` and `CMS_INFOOBJECTS7`. Querying physical tables directly yields unreadable binary streams, is unsupported by SAP, and risks table locks on the production CMS.
- **Why `POST /biprws/v1/cmsquery` + Raylight is Used:**
  The WACS REST endpoint delegates in-memory BLOB decompression to the CMS subsystem, returning decoded JSON containing `SI_STATUSINFO`, substitution strings (`SI_SUBST_STRINGS`), timestamps, and owner metadata using the standard `X-SAP-LogonToken`.

---

## 2. Diagnostic Pipeline (`DiagnosticService.diagnose_batch`)

```
[1. CMS Scan] ──> POST /biprws/v1/cmsquery (WHERE SI_SCHEDULE_STATUS = 3)
                         │
                         ▼
[2. Recursive Error Extraction] ──> Flatten SI_STATUSINFO & SI_SUBST_STRINGS
                         │
                         ▼
[3. Signature Normalization] ──> Isolate SAP codes (IES, WIS, ORA, FBE) & strip volatile PIDs/IPs/timestamps
                         │
                         ▼
[4. SHA-256 Clustering] ──> Deduplicate failures into ClusterDiagnosis buckets
                         │
                         ▼
[5. Smart Enrichment] ──> Query /raylight/v1/documents/{id}/parameters for prompt-related clusters
                         │
                         ▼
[6. Heuristic Classification] ──> Assign Top-3 PotentialCauses + Remediation Steps (Pydantic v2)
```

---

## 3. Pydantic v2 Data Contracts (`core/models.py`)

All diagnostic outputs are strictly validated via Pydantic v2 models (`extra="forbid"`):

- **`FailureCategory` (Enum):**
  - `NETWORK_TIMEOUT`
  - `AUTH_CREDENTIALS`
  - `MISSING_PROMPTS`
  - `DB_LOCK_CONCURRENCY`
  - `SERVER_RESOURCE_OOM`
  - `CACHE_CORRUPTED`
  - `BURSTING_RECIPIENT`
  - `UNKNOWN_GENERIC`
- **`PotentialCause`:**
  - `rank` (`1..3`), `probability_score` (`0.0..1.0`), `category`, `title`, `technical_explanation`, and `recommended_actions` (`List[str]`).
- **`ClusterDiagnosis`:**
  - `cluster_id` (deterministic hash), `error_signature`, `affected_count`, `sample_instance_ids`, `sample_report_names`, and `top_causes` (up to 3 ranked causes).
- **`BatchDiagnosticsReport`:**
  - `scan_timestamp`, `hours_back`, `kind`, `folder_id`, `total_failed_instances`, `clusters_count`, `is_truncated`, `clusters`, and `executive_summary`.

---

## 4. Resilience & Edge Cases

1. **Clean Batch Night (`0` failures):** Returns `total_failed_instances = 0` and an empty `clusters` list with a clear confirmation summary.
2. **Empty or Truncated `SI_STATUSINFO`:** Falls back to `SI_ERROR_SEARCH_KEY` and execution duration (`SI_ENDTIME - SI_STARTTIME`) to detect abrupt server crashes.
3. **Orphan Instances (HTTP 404):** Safely catches `404` responses during Raylight parameter enrichment if the parent document was deleted after the instance failed.
4. **Failure Storms:** Paginates CMS scans up to `max_instances` and sets `is_truncated = True` to protect both WACS gateways and LLM context windows.
5. **Mandatory IDT Rule Enforcement:** Remediation instructions generated for database connectivity (`IES 10901`, `ORA-01017`) strictly direct administrators to test connections in **Information Design Tool (IDT)** (or **UDT** for `.unv`), never in the CMC. See [Relational Connections & IDT Testing Rules](../sap_bo/connections_and_idt.md).
