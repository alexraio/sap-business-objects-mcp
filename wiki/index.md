---
type: index
title: SAP BusinessObjects MCP (bo-mcp) LLM-Wiki
description: Root Open Knowledge Format (OKF) catalog and progressive disclosure entry point for the SAP BusinessObjects 4.3 SP5 MCP Server knowledge wiki.
status: active
last_updated: 2026-11-06
tags:
  - okf
  - llm-wiki
  - sap-bo
  - mcp
  - index
related:
  - ./log.md
  - ./raw/README.md
  - ./architecture/index.md
  - ./sap_bo/index.md
  - ./tools/index.md
  - ./troubleshooting/index.md
---

# SAP BusinessObjects MCP (`bo-mcp`) LLM-Wiki

Welcome to the compiled **LLM-Wiki** for the **SAP BusinessObjects BI Platform 4.3 SP5 MCP Server**.
This self-contained `wiki/` folder combines **Andrej Karpathy's LLM-Wiki pattern** (*compile once, query fast forever*) and **Google Cloud's Open Knowledge Format (OKF)** specification.

> **For AI Agents:** Read this `wiki/index.md` first to locate relevant domain concepts, architectural specs, tool contracts, or troubleshooting runbooks via progressive disclosure. Follow [`.agents/rules/wiki_operations.md`](../.agents/rules/wiki_operations.md) for `QUERY`, `INGEST`, and `LINT` operations.

---

## 1. Architecture & Engineering (`wiki/architecture/`)

| Concept Page | Summary |
| :--- | :--- |
| [Architecture Section Index](./architecture/index.md) | Overview of internal server design and architectural specifications. |
| [System Overview & Layered Design](./architecture/system_overview.md) | Topology of `server.py`, `BOESDKParser` facade, `BOEClient`, and the 6 domain services. |
| [Enterprise Authentication & Session Isolation](./architecture/authentication_and_sessions.md) | Chained credential resolution (`.env` $\rightarrow$ OS Keyring), `SecretStr` safety, CLI setup wizard, and `SessionManager` isolation. |
| [Intelligent Diagnostics Engine](./architecture/intelligent_diagnostics_engine.md) | Automated batch failure Root Cause Analysis (`DiagnosticService`), SHA-256 signature clustering, and Pydantic v2 models. |
| [Remote HTTP / SSE Deployment Roadmap](./architecture/remote_sse_roadmap.md) | Roadmap for multi-tenant HTTP/SSE/Streamable-HTTP enterprise gateway deployment. |

---

## 2. SAP BusinessObjects 4.3 SP5 Domain (`wiki/sap_bo/`)

| Concept Page | Summary |
| :--- | :--- |
| [SAP BO Domain Section Index](./sap_bo/index.md) | Overview of SAP BusinessObjects 4.3 SP5 platform architecture and APIs. |
| [CMS Query Language & Virtual Tables](./sap_bo/cms_query_language.md) | `CI_INFOOBJECTS`, `CI_SYSTEMOBJECTS`, `CI_APPOBJECTS` schemas, CMS SQL syntax constraints (no `JOIN` / `GROUP BY`), and query templates. |
| [Relational Connections & IDT Testing Rules](./sap_bo/connections_and_idt.md) | **Mandatory Rule:** CMC has no Test Connection button for relational connections; always use **Information Design Tool (IDT)** for UNX or **UDT** for UNV. |
| [Semantic Layer, Universes & Change Data Source](./sap_bo/semantic_layer_and_universes.md) | UNX vs. UNV universes, `/sl/v1/universes` inspection, lineage queries, and automated Change Data Source mapping strategies (`SameID`, `SamePath`, `SameName`). |
| [Web Intelligence & Raylight REST Lifecycle](./sap_bo/webi_raylight_lifecycle.md) | In-memory session state, prompt/LOV resolution, `/dataset` tabular extraction, and content-negotiated exports (`PDF`, `XLSX`, `CSV` with `refresh=True`). |

---

## 3. MCP Tool Catalogs & Safety Tiers (`wiki/tools/`)

| Concept Page | Summary |
| :--- | :--- |
| [Tools Section Index & Safety Tiers](./tools/index.md) | Classification of **Tier 1 (Read-Only)** vs. **Tier 2 (State-Altering / Confirmation Required)** tools. |
| [Semantic Layer & Web Intelligence Tools](./tools/catalog_semantic_and_webi.md) | 24 tools for authentication, universes, Webi lifecycle, prompts, tabular block data, exports, and Change Data Source. |
| [CMS Administration, Security & InfoStore Tools](./tools/catalog_cms_admin_and_infostore.md) | 14 tools for `cms_query`, users, user groups, active sessions, folders, and corporate categories. |
| [Schedules, Instances & Batch Diagnostics Tools](./tools/catalog_schedules_and_diagnostics.md) | 5 tools for recurring schedules, historical instances, and `diagnose_batch_failures`. |

---

## 4. Troubleshooting & Error Runbooks (`wiki/troubleshooting/`)

| Concept Page | Summary |
| :--- | :--- |
| [Troubleshooting Section Index](./troubleshooting/index.md) | Triage matrix for SAP BusinessObjects error codes. |
| [IES 10901: Database Connectivity Failure](./troubleshooting/ies_10901_database_connectivity.md) | OS/network TCP verification vs. mandatory IDT relational connection testing. |
| [WIS 30553 & WSR 00999: Webi Timeout & OOM](./troubleshooting/wis_30553_webi_processing_timeout.md) | Query volume analysis, complex formula tuning, and CMC Webi Processing Server memory/timeout sizing. |
| [ORA-01017 & Database Authentication Failures](./troubleshooting/ora_01017_and_db_auth.md) | Account unlock workflow and credential rotation in Information Design Tool (IDT). |
| [WSR 00400, Session Expiry & FRS Storage Errors](./troubleshooting/wsr_00400_and_session_expiry.md) | Handling expired `X-SAP-LogonToken` headers, `FWM 02024` FileStore errors, and `FBE60502` Publication bursting issues. |

---

## 5. Governance, Raw Sources & History

- **Chronological Change Log:** [wiki/log.md](./log.md)
- **Immutable Raw Sources:** [wiki/raw/README.md](./raw/README.md)
- **Wiki Operational Protocol:** [.agents/rules/wiki_operations.md](../.agents/rules/wiki_operations.md)
