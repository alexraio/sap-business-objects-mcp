---
type: index
title: SAP BusinessObjects 4.3 SP5 Domain Knowledge Index
description: Navigation index for SAP BusinessObjects BI Platform 4.3 SP5 domain architecture, CMS SQL, relational connections, universes, and Web Intelligence Raylight APIs.
status: active
last_updated: 2026-11-06
tags:
  - sap-bo
  - domain
  - index
related:
  - ../index.md
  - ./cms_query_language.md
  - ./connections_and_idt.md
  - ./semantic_layer_and_universes.md
  - ./webi_raylight_lifecycle.md
---

# SAP BusinessObjects 4.3 SP5 Domain Knowledge (`wiki/sap_bo/`)

This section contains compiled, verified domain truths for interacting with **SAP BusinessObjects BI Platform 4.3 SP5** via RESTful Web Services (`biprws`, `raylight/v1`, `sl/v1`).

## Pages in this Section

| Page | Type | Summary |
| :--- | :--- | :--- |
| [CMS Query Language & Virtual Tables](./cms_query_language.md) | `sap_domain` | Virtual table schemas (`CI_INFOOBJECTS`, `CI_SYSTEMOBJECTS`, `CI_APPOBJECTS`), CMS SQL grammar limitations, and query templates. |
| [Relational Connections & IDT Testing Rules](./connections_and_idt.md) | `sap_domain` | Architecture of `.cnx` / `.cns` / `.unv` connections and the mandatory rule: **CMC has no Test Connection button; test in IDT or UDT**. |
| [Semantic Layer, Universes & Change Data Source](./semantic_layer_and_universes.md) | `sap_domain` | UNX vs. UNV universes, object lineage queries, and automated Change Data Source mapping strategies (`SameID`, `SamePath`, `SameName`, etc.). |
| [Web Intelligence & Raylight REST Lifecycle](./webi_raylight_lifecycle.md) | `sap_domain` | Document state, parameters/LOVs, Data Provider SQL extraction, `/dataset` tabular extraction, and in-session binary exports (PDF/XLSX/CSV). |

## Related Sections
- [Architecture & System Design](../architecture/index.md)
- [MCP Tool Catalogs](../tools/index.md)
- [Troubleshooting & Error Runbooks](../troubleshooting/index.md)
