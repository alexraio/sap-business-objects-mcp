---
type: index
title: Architecture & System Design Index
description: Navigation index for the internal architecture, authentication, session management, and diagnostic engine of the SAP BusinessObjects MCP server.
status: active
last_updated: 2026-11-09
tags:
  - architecture
  - index
  - fastmcp
related:
  - ../index.md
  - ./system_overview.md
  - ./authentication_and_sessions.md
  - ./intelligent_diagnostics_engine.md
  - ./remote_sse_roadmap.md
---

# Architecture & System Design (`wiki/architecture/`)

This section documents the internal engineering architecture, design decisions, and roadmap of the `bo-mcp` server.

## Pages in this Section

| Page | Type | Summary |
| :--- | :--- | :--- |
| [System Overview & Layered Design](./system_overview.md) | `architecture` | High-level topology of `server.py`, `BOESDKParser` facade, `BOEClient` HTTP layer, and specialized domain services. |
| [Enterprise Authentication & Session Isolation](./authentication_and_sessions.md) | `architecture` | Multi-tier credential resolution (`.env` $\rightarrow$ OS Keyring), `SecretStr` protection, CLI setup wizard, and `SessionManager` isolation. |
| [Intelligent Diagnostics Engine](./intelligent_diagnostics_engine.md) | `architecture` | Architecture of `DiagnosticService`, SHA-256 failure clustering, Pydantic v2 contracts, and RESTful WACS vs. direct CMS DB trade-offs. |
| [Co-Located Remote MCP Server, Local Log Analyzer & ODBC Auditing Architecture](./remote_sse_roadmap.md) | `architecture` | Validated design for native Linux/Windows co-located HTTP/SSE service, multi-tenant RBAC, `.glf` `LogService`, and `pyodbc` `AuditService`. |

## Related Sections
- [SAP BusinessObjects Domain Knowledge](../sap_bo/index.md)
- [MCP Tool Catalogs](../tools/index.md)
- [Troubleshooting & Error Runbooks](../troubleshooting/index.md)
