---
type: tool_catalog
title: CMS Administration, Security & InfoStore Tools Catalog
description: Complete reference of MCP tools for CMS SQL queries, user and group administration, active session auditing, folder management, and corporate categories.
status: active
last_updated: 2026-11-06
tags:
  - tools
  - cms
  - users
  - sessions
  - infostore
related:
  - ./index.md
  - ../sap_bo/cms_query_language.md
  - ../architecture/system_overview.md
---

# CMS Administration, Security & InfoStore Tools Catalog

This catalog documents the MCP tools registered in [`server.py`](../../server.py) for CMS repository administration (`services/admin_service.py`) and InfoStore folder navigation (`services/infostore_service.py`).

---

## 1. Central Management Server (CMS) Query Tool

| Tool Name | Tier | Signature | Description |
| :--- | :---: | :--- | :--- |
| `cms_query` | Tier 1 | `cms_query(query: str, page: int = 1, pagesize: int = 1000) -> Dict[str, Any]` | Executes a native CMS SQL `SELECT` query against `CI_INFOOBJECTS`, `CI_SYSTEMOBJECTS`, or `CI_APPOBJECTS` via `POST /biprws/v1/cmsquery`. See [CMS Query Language](../sap_bo/cms_query_language.md). |

---

## 2. User, Group & Session Administration Tools

| Tool Name | Tier | Signature | Description |
| :--- | :---: | :--- | :--- |
| `get_users` | Tier 1 | `get_users(page: int = 1, pagesize: int = 100) -> List[Dict[str, Any]]` | Lists user accounts (`id`, `name`, `email`, `disabled`, `lastLogon`). |
| `get_user_details` | Tier 1 | `get_user_details(user_id: str) -> Dict[str, Any]` | Retrieves full profile properties for a specific user ID. |
| `set_user_status` | **Tier 2** | `set_user_status(user_id: str, disabled: bool) -> str` | Enables (`disabled=False`) or disables (`disabled=True`) a user account. **Requires confirmation.** |
| `get_user_groups` | Tier 1 | `get_user_groups(page: int = 1, pagesize: int = 100) -> List[Dict[str, Any]]` | Lists configured user groups and member counts. |
| `get_group_users` | Tier 1 | `get_group_users(group_id: str) -> List[Dict[str, str]]` | Lists all user accounts belonging to a specific user group. |
| `get_active_sessions` | Tier 1 | `get_active_sessions() -> List[Dict[str, Any]]` | Lists active user sessions currently open on the CMS cluster. |
| `terminate_session` | **Tier 2** | `terminate_session(session_id: str) -> str` | Forcibly disconnects an active session by ID to free licenses or clear hung connections. **Requires confirmation.** |

---

## 3. InfoStore Folders & Categories Tools

| Tool Name | Tier | Signature | Description |
| :--- | :---: | :--- | :--- |
| `get_folders` | Tier 1 | `get_folders(folder_id: str) -> List[str]` | Recursively retrieves all subfolder IDs starting from a parent `folder_id` (use `'0'` or `'23'` for root public folders). |
| `get_folder_details` | Tier 1 | `get_folder_details(folder_id: str) -> Dict[str, Any]` | Retrieves folder metadata (`name`, `cuid`, `parent_id`, `description`). |
| `create_folder` | **Tier 2** | `create_folder(name: str, parent_folder_id: str, description: Optional[str] = None) -> Dict[str, Any]` | Creates a new InfoStore folder under `parent_folder_id`. **Requires confirmation.** |
| `delete_folder` | **Tier 2** | `delete_folder(folder_id: str) -> str` | Permanently deletes a repository folder. Always check for child objects first. **Requires confirmation.** |
| `get_webi_docs` | Tier 1 | `get_webi_docs(folder_id: str) -> List[str]` | Lists Web Intelligence document IDs located directly inside `folder_id`. |
| `get_categories` | Tier 1 | `get_categories() -> List[Dict[str, str]]` | Lists Corporate Categories defined in the BI repository. |
