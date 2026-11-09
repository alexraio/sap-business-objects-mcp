---
type: index
title: MCP Tool Catalogs & Safety Tiers Index
description: Navigation index for all 40+ SAP BusinessObjects MCP tools, action safety tiers (Tier 1 Read-Only vs Tier 2 State-Altering), and intent routing.
status: active
last_updated: 2026-11-09
tags:
  - tools
  - mcp
  - safety-tiers
  - index
related:
  - ../index.md
  - ./catalog_semantic_and_webi.md
  - ./catalog_cms_admin_and_infostore.md
  - ./catalog_schedules_and_diagnostics.md
---

# MCP Tool Catalogs & Safety Tiers (`wiki/tools/`)

This section documents all MCP tools exposed by [`server.py`](../../server.py), categorized by domain and operational safety tier.

---

## 1. Action Safety Tiers

To protect production BI environments against accidental mutations or deletions, every tool is assigned a safety tier:

- **Tier 1 (Safe / Read-Only — Autonomous Execution):**
  - Inspection, discovery, metadata querying (`SELECT`), diagnostic scanning, in-session refreshing, and local file exports.
  - Agents may invoke Tier 1 tools autonomously.
- **Tier 2 (State-Altering / Destructive — Mandatory User Confirmation):**
  - Operations that overwrite repository documents, purge cached data, repoint universes, disable user accounts, terminate active sessions, or delete objects (`delete_webi_doc`, `delete_instance`, `delete_folder`, `terminate_session`, `set_user_status`, `save_webi_doc`, `purge_dp`, `change_dp_datasource`).
  - **Protocol:** Before invoking any Tier 2 tool, the agent **must** present the target object's ID, name, parent context, and expected impact, and wait for explicit user approval.

---

## 2. Tool Catalog Pages

| Catalog Page | Domains Covered | Tool Count |
| :--- | :--- | :--- |
| [Semantic Layer & Web Intelligence Tools](./catalog_semantic_and_webi.md) | Authentication (`login`/`logout`), Universes, Webi Lifecycle, Exports, Prompts/LOVs, Tabs/Blocks, Data Providers, and Change Data Source. | 24 tools |
| [CMS Administration, Security & InfoStore Tools](./catalog_cms_admin_and_infostore.md) | CMS SQL Queries (`cms_query`), Users & Groups, Active Sessions, InfoStore Folders, and Corporate Categories. | 14 tools |
| [Schedules, Instances & Batch Diagnostics Tools](./catalog_schedules_and_diagnostics.md) | Document Schedules, Historical Run Instances, Intelligent Diagnostics (`diagnose_batch_failures`), Local `.glf` Log Inspection (`LogService`), Auditing DB ODBC Introspection (`AuditService`), and Remote Self-Diagnostics (`get_mcp_server_diagnostics`). | 13 tools |

## Related Sections
- [Architecture & System Design](../architecture/index.md)
- [SAP BusinessObjects Domain Knowledge](../sap_bo/index.md)
- [Troubleshooting & Error Runbooks](../troubleshooting/index.md)
