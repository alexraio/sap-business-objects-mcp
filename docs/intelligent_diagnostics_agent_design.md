# Design Document: Intelligent Diagnostics Agent for SAP BusinessObjects

## 1. Executive Summary

Managing nocturnal batch executions and mass multi-recipient publications (bursting) within the Central Management Console (CMC) creates a significant operational workload for SAP BusinessObjects administrators. When hundreds or thousands of instances run, failures often produce fragmented or generic native error messages (`SI_STATUSINFO`), delaying Root Cause Analysis (RCA).

The **Intelligent Diagnostics Agent** automates systematic health monitoring and incident triage via the Model Context Protocol (FastMCP). The system executes targeted scans against `CI_INFOOBJECTS` using `POST /biprws/v1/cmsquery`, normalizes and clusters failures by deterministic error signatures, enriches diagnostic context via Web Intelligence parameter inspection, and generates a programmatic diagnostic report powered by **Pydantic v2**. For each identified failure cluster, the agent delivers **up to 3 ranked probable causes** with confidence scores and **actionable, step-by-step administrator remediation instructions**.

---

## 2. Technical Evaluation Findings (RESTful vs. Direct CMS Database Connection)

- **Why the CMS Database Cannot Be Queried via Direct SQL:**  
  The underlying relational CMS database (Oracle, Microsoft SQL Server, SAP HANA, IBM DB2) stores extended metadata (`SI_SCHEDULEINFO`, prompt parameters, destinations, error logs) in **proprietary compressed binary BLOBs** within physical tables like `CMS_INFOOBJECTS5` and `CMS_INFOOBJECTS7`. Querying these tables directly returns unreadable binary payloads, is unsupported by SAP, and risks causing critical table locks on the active CMS repository.
- **Why the RESTful Suite (`biprws` + Raylight) Is the Native and Complete Solution:**  
  The endpoint `POST /biprws/v1/cmsquery` delegates in-memory BLOB decompression to the CMS subsystem, returning clean, structured JSON containing `SI_SCHEDULE_STATUS = 3`, `SI_STATUSINFO`, `SI_STARTTIME`, `SI_ENDTIME`, `SI_OWNER`, prompts, and schedule parameters.
- **Verdict:** Integration is **100% RESTful Web Services** utilizing the WACS session token (`X-SAP-LogonToken`) managed by `BOEClient`. No physical database connectors or proprietary Java SDK runtimes are required.

---

## 3. Decision Log

| # | Topic | Adopted Decision | Evaluated Alternatives | Rationale |
|---|---|---|---|---|
| **D1** | Operating Mode | **Diagnostic & Audit Only (Read-Only)** | Autonomous auto-healing; Assisted rescheduling | Eliminates all operational risk on the production CMS, providing high-precision RCA and actionable guidance for human administrators. |
| **D2** | Integration Channel | **100% RESTful WACS (`POST /biprws/v1/cmsquery` + Raylight)** | Direct SQL connector on CMS DB; Java SDK | Physical CMS DB tables use unreadable binary BLOBs. `cmsquery` delivers native, decoded structured JSON. |
| **D3** | Object Scope | **Both: Webi Reports and Publications (Bursting)** | Webi Only; Publications Only | Provides complete coverage across the entire nocturnal enterprise batch schedule. |
| **D4** | Scalability & Volume | **Pagination with Pre-Processing & Clustering (Error Signatures)** | Sequential full scan; Blind TOP-N sampling | Prevents LLM context exhaustion and WACS gateway timeouts by deduplicating failures sharing the same root cause. |
| **D5** | Diagnostic Structure | **Ranked Top-3 Probable Causes with Actionable Steps** | Forced single cause; Generic prose diagnostics | Enterprise BI failures are frequently polymorphic; a 3-tier ranked assessment with probability scores guides triage efficiently. |
| **D6** | Programmatic Engine | **Pydantic v2 Native Structured Outputs** | CrewAI; LangGraph | Zero heavy framework dependencies, 100% type safety, sub-second execution latency, and zero syntax hallucinations. |

---

## 4. Architecture & Components

```text
┌────────────────────────────────────────────────────────┐
│                   AI Agent Surface                     │
│    (Google Antigravity IDE / Antigravity CLI "agy")    │
└───────────────────────────▲────────────────────────────┘
                            │ MCP Protocol (JSON-RPC over STDIO)
┌───────────────────────────▼────────────────────────────┐
│              FastMCP Server (server.py)                │
│    Tool: diagnose_batch_failures(hours_back, kind,...) │
└───────────────────────────▲────────────────────────────┘
                            │ Internal Invocation
┌───────────────────────────▼────────────────────────────┐
│       DiagnosticService (services/diagnostic_service.py)│
│  - scan_failed_instances()                             │
│  - extract_error_signature() & cluster_failures()       │
│  - smart_enrichment() (Webi prompts & publication)     │
│  - Pydantic v2 Models Validation                        │
└───────────────────────────▲────────────────────────────┘
                            │ HTTP (X-SAP-LogonToken)
┌───────────────────────────▼────────────────────────────┐
│      SAP BusinessObjects BI Platform 4.3 (WACS)        │
│  - POST /biprws/v1/cmsquery (CI_INFOOBJECTS)           │
│  - GET /biprws/raylight/v1/documents/{id}/parameters   │
│  - GET /biprws/v1/publications/{id}                    │
└────────────────────────────────────────────────────────┘
```

### Core Components:

1. **`core/models.py` (Pydantic v2 Data Contracts):**
   - `FailureCategory`: Standardized enum classifying root causes (Network Timeout, DB Authentication, Missing Prompts, DB Deadlock, Server OOM, Corrupted Cache, Bursting Recipient, Generic).
   - `PotentialCause`: Model representing an individual ranked cause (`rank` 1..3, `probability_score`, `category`, `title`, `technical_explanation`, `recommended_actions`).
   - `ClusterDiagnosis`: Model for an aggregated error cluster (`cluster_id`, `error_signature`, `affected_count`, `sample_instance_ids`, `sample_report_names`, `top_causes` max 3).
   - `BatchDiagnosticsReport`: Root report model (`scan_timestamp`, `hours_back`, `kind`, `total_failed_instances`, `clusters_count`, `clusters`, `executive_summary`, `is_truncated`).

2. **`services/diagnostic_service.py`:**
   - Queries the CMS repository for instances with `SI_SCHEDULE_STATUS = 3`.
   - Recursively flattens nested CMS error structures (`SI_STATUSINFO`, `SI_SUBST_STRINGS`, `SI_RESOURCEID`).
   - Normalizes error messages into deterministic signatures by isolating standard failure codes (`WIS`, `ORA`, `CRS`, `FBE`) and stripping volatile noise (timestamps, PIDs, IP addresses).
   - Clusters failures using SHA-256 fingerprinting.
   - Enriches prompt-related clusters via `/raylight/v1/documents/{id}/parameters`.
   - Returns the strictly validated `BatchDiagnosticsReport`.

3. **`server.py`:**
   - Exposes the typed FastMCP tool `@mcp.tool() def diagnose_batch_failures(...)`.

---

## 5. Pydantic Data Contract (Specification)

```python
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class FailureCategory(str, Enum):
    """Standardized root cause failure classification for SAP BO batch executions."""

    NETWORK_TIMEOUT = "Infrastruttura / Timeout Rete"
    AUTH_CREDENTIALS = "Credenziali / Autenticazione DB"
    MISSING_PROMPTS = "Prompt Obbligatori Mancanti"
    DB_LOCK_CONCURRENCY = "Lock Tabelle / Concorrenza DB"
    SERVER_RESOURCE_OOM = "Saturazione Risorse / Memoria WACS-APS"
    CACHE_CORRUPTED = "Corruzione Cache Data Provider"
    BURSTING_RECIPIENT = "Errore Destinatari Dinamici Pubblicazione"
    UNKNOWN_GENERIC = "Eccezione Non Classificata"


class PotentialCause(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    rank: int = Field(..., ge=1, le=3, description="Priority rank from 1 (highest) to 3")
    probability_score: float = Field(..., ge=0.0, le=1.0, description="Estimated confidence score from 0.0 to 1.0")
    category: FailureCategory = Field(..., description="Standardized failure category")
    title: str = Field(..., min_length=1, description="Concise title of the potential root cause")
    technical_explanation: str = Field(
        ..., min_length=1, description="Detailed technical analysis linked to error traces"
    )
    recommended_actions: List[str] = Field(
        ..., min_length=1, description="Step-by-step actionable remediation instructions"
    )


class ClusterDiagnosis(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    cluster_id: str = Field(..., description="Deterministic hash identifier for the cluster")
    error_signature: str = Field(..., description="Normalized error message signature")
    affected_count: int = Field(..., ge=1, description="Total number of failed instances")
    sample_instance_ids: List[str] = Field(..., description="Sample instance IDs")
    sample_report_names: List[str] = Field(..., description="Sample affected report names")
    top_causes: List[PotentialCause] = Field(..., max_length=3, description="Up to 3 most probable root causes")


class BatchDiagnosticsReport(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    scan_timestamp: str = Field(..., description="ISO 8601 timestamp of the diagnostic scan")
    hours_back: int = Field(..., ge=1, description="Time window in hours analyzed")
    kind: str = Field(default="All", description="Kind of objects scanned (Webi, Publication, All)")
    folder_id: Optional[str] = Field(default=None, description="Folder ID filter if specified")
    total_failed_instances: int = Field(..., ge=0, description="Total failed instances intercepted")
    clusters_count: int = Field(..., ge=0, description="Number of distinct error clusters")
    is_truncated: bool = Field(default=False, description="True if failures exceeded scan limit")
    clusters: List[ClusterDiagnosis] = Field(default_factory=list, description="Deduplicated clusters")
    executive_summary: str = Field(..., description="High-level executive summary and action items")
```

---

## 6. Error Handling & Edge Cases

1. **Zero Failures (`Clean Batch Night`):** Returns `total_failed_instances = 0`, an empty cluster list, and a reassuring executive summary confirming all scheduled executions completed successfully.
2. **Empty or Truncated Error Payloads:** Falls back to `SI_ERROR_SEARCH_KEY` and execution duration metrics (`SI_ENDTIME - SI_STARTTIME`), classifying the failure as an abnormal process termination or server stop.
3. **Orphan Objects:** Gracefully traps HTTP 404 responses during prompt inspection if parent documents were deleted post-execution.
4. **Massive Failure Storms:** Implements controlled pagination and sets `is_truncated = True` in the report to highlight widespread infrastructure blackouts without saturating WACS gateways or LLM context windows.

---

## 7. Operational Guidelines: Relational Connection Testing

> [!IMPORTANT]
> In SAP BusinessObjects 4.x, the Central Management Console (CMC) does **not** provide a "Test Connection" function for relational connections.
> Relational connection testing (`.cns` / `.cnx` for UNX) is supported exclusively through the **Information Design Tool (IDT)** (or Universe Design Tool for legacy `.unv`).
> Administrators must never be instructed to test database connectivity within the CMC.

---

## 8. Testing & Validation Strategy

- **Offline Unit Test Suite (`tests/test_diagnostic_service.py`):**
  - Regex signature normalization across real-world SAP BO error codes (`WIS 30553`, `ORA-00060`, `FBE60502`, socket timeouts).
  - Clustering and deduplication of 50+ simulated instances into distinct root cause groups.
  - Strict Pydantic v2 contract validation (maximum 3 causes per cluster, rank bounds 1..3, probability scores between 0.0 and 1.0).
  - Edge case handling (clean batch night, missing `SI_STATUSINFO`, deleted orphan documents, pagination truncation).
- **Tool Integration Tests (`tests/test_server_tools.py`):**
  - Verification of `diagnose_batch_failures` tool registration and JSON schema compliance.
- **CI/CD Automation:**
  - Automated execution via GitHub Actions under Python 3.13 with `pytest --cov` and `ruff` linting.
