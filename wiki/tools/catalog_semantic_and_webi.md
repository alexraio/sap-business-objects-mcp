---
type: tool_catalog
title: Semantic Layer & Web Intelligence Tools Catalog
description: Complete reference of MCP tools for authentication, universes, Web Intelligence documents, prompts, tabular data extraction, binary exports, and Change Data Source.
status: active
last_updated: 2026-11-06
tags:
  - tools
  - webi
  - universe
  - export
  - dataprovider
related:
  - ./index.md
  - ../sap_bo/semantic_layer_and_universes.md
  - ../sap_bo/webi_raylight_lifecycle.md
  - ../sap_bo/connections_and_idt.md
---

# Semantic Layer & Web Intelligence Tools Catalog

This catalog documents the MCP tools registered in [`server.py`](../../server.py) for authentication, Semantic Layer universes (`services/universe_service.py`), and Web Intelligence operations (`services/webi_service.py`).

---

## 1. Authentication Tools

| Tool Name | Tier | Signature | Description |
| :--- | :---: | :--- | :--- |
| `login` | Tier 1 | `login(username: Optional[str] = None, password: Optional[str] = None) -> str` | Acquires an active `X-SAP-LogonToken`. Resolves credentials automatically from `.env` or OS Keyring if arguments are omitted. |
| `logout` | Tier 1 | `logout() -> str` | Logs off via `POST /biprws/v1/logoff` and releases the SAP BO session license. |

---

## 2. Semantic Layer & Universe Tools

| Tool Name | Tier | Signature | Description |
| :--- | :---: | :--- | :--- |
| `get_universes` | Tier 1 | `get_universes() -> List[Dict[str, str]]` | Lists all published UNX and UNV universes (`id`, `name`, `folderId`). |
| `get_universe_details` | Tier 1 | `get_universe_details(universe_id: str) -> Dict[str, str]` | Returns universe engine type (`unx` or `unv`), CUID, and technical metadata. |
| `get_universe_structure` | Tier 1 | `get_universe_structure(universe_id: str) -> Dict[str, Any]` | Retrieves the business layer object tree (classes, dimensions, measures, attributes) from `/sl/v1/universes/{id}`. |
| `get_universe_related_reports` | Tier 1 | `get_universe_related_reports(universe_id: str) -> Dict[str, Any]` | Returns all Webi documents bound to the universe for lineage and blast-radius analysis. |
| `get_universe_connection_id` | Tier 1 | `get_universe_connection_id(universe_id: str) -> Optional[str]` | Retrieves the relational `CCIS.DataConnection` ID linked to the universe. *(Test connections strictly in IDT/UDT, never CMC).* |

---

## 3. Webi Document Lifecycle & Export Tools

| Tool Name | Tier | Signature | Description |
| :--- | :---: | :--- | :--- |
| `get_documents` | Tier 1 | `get_documents(page: int = 1, pagesize: int = 50) -> List[Dict[str, Any]]` | Lists accessible Webi documents with `id`, `cuid`, `name`, `folderId`, and `updated`. |
| `get_doc_details` | Tier 1 | `get_doc_details(webi_doc_id: str) -> Optional[Dict[str, Any]]` | Returns document name, repository folder path, CUID, scheduled flag, and state. |
| `get_doc_properties` | Tier 1 | `get_doc_properties(webi_doc_id: str) -> Dict[str, Any]` | Returns configuration flags (`refreshOnOpen`, `usePersonalData`, locale). |
| `save_webi_doc` | **Tier 2** | `save_webi_doc(webi_doc_id: str, webi_doc_name: Optional[str] = None) -> str` | Saves document in-place (`PUT`) or as a named copy (`POST`). **Requires confirmation.** |
| `delete_webi_doc` | **Tier 2** | `delete_webi_doc(webi_doc_id: str) -> str` | Permanently deletes a Webi document from the CMS. **Requires confirmation.** |
| `export_webi_doc` | Tier 1 | `export_webi_doc(webi_doc_id: str, export_format: str = "pdf", report_id: Optional[str] = None, output_path: Optional[str] = None, refresh: bool = False) -> Dict[str, Any]` | Exports document or tab to `pdf`, `xlsx`, `csv`, or `all`. When `refresh=True`, executes an in-session refresh immediately prior to streaming. |

---

## 4. Prompts, Parameters & Document Refresh Tools

| Tool Name            |  Tier  | Signature                                                                                                 | Description                                                                                                  |
| :------------------- | :----: | :-------------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------- |
| `get_doc_parameters` | Tier 1 | `get_doc_parameters(webi_doc_id: str) -> List[Dict[str, Any]]`                                            | Lists required and optional prompt parameters (`id`, `name`, `technicalName`, `cardinality`, `constrained`). |
| `get_parameter_lov`  | Tier 1 | `get_parameter_lov(webi_doc_id: str, parameter_id: int) -> List[Any]`                                     | Retrieves the allowed List of Values (LOV) for a constrained prompt parameter.                               |
| `refresh_webi_doc`   | Tier 1 | `refresh_webi_doc(webi_doc_id: str, parameters: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]` | Refreshes all document queries in memory, optionally passing prompt answers `[{"id": 0, "value": "2026"}]`.  |

---

## 5. Tabs, Elements, Tabular Data, Variables & Comments

| Tool Name | Tier | Signature | Description |
| :--- | :---: | :--- | :--- |
| `get_reports` | Tier 1 | `get_reports(webi_doc_id: str) -> List[Dict[str, Any]]` | Lists report tabs/sheets (`id`, `name`) inside a Webi document. |
| `get_report_elements` | Tier 1 | `get_report_elements(webi_doc_id: str, report_id: str) -> List[Dict[str, Any]]` | Lists tables, charts, forms, and layout elements on a report tab. |
| `get_report_element_data` | Tier 1 | `get_report_element_data(webi_doc_id: str, report_id: str, element_id: str, max_rows: int = 1000) -> Dict[str, Any]` | Extracts column headers and structured row dictionaries from a table/chart element via `/dataset` (capped at `max_rows`). |
| `get_variables` | Tier 1 | `get_variables(webi_doc_id: str) -> List[Dict[str, Any]]` | Lists custom report variables and formulas (`id`, `name`, `qualification`, `formula`). |
| `get_comments` | Tier 1 | `get_comments(webi_doc_id: str) -> List[Dict[str, Any]]` | Retrieves collaborative comments and annotations on the document. |

---

## 6. Data Providers, SQL & Change Data Source Tools

| Tool Name | Tier | Signature | Description |
| :--- | :---: | :--- | :--- |
| `get_dp` | Tier 1 | `get_dp(webi_doc_id: str) -> List[str]` | Lists Data Provider IDs (e.g., `['DP0', 'DP1']`). |
| `get_dp_details` | Tier 1 | `get_dp_details(webi_doc_id: str, dp_id: str) -> Optional[Dict[str, Any]]` | Returns data source ID, name, type, and update status for a Data Provider. |
| `get_dp_sql` | Tier 1 | `get_dp_sql(webi_doc_id: str, dp_id: str) -> str` | Extracts the native SQL statement generated by the Semantic Layer (`/queryplan`). |
| `get_dp_specification` | Tier 1 | `get_dp_specification(webi_doc_id: str, dp_id: str) -> Dict[str, Any]` | Returns the XML/JSON query specification (result objects, filters, sorts). |
| `refresh_dp` | Tier 1 | `refresh_dp(webi_doc_id: str, dp_id: str) -> str` | Refreshes a single Data Provider in memory. |
| `purge_dp` | **Tier 2** | `purge_dp(webi_doc_id: str, dp_id: str) -> str` | Purges cached microcube rows from a Data Provider. **Requires confirmation.** |
| `get_dp_mapping_proposal` | Tier 1 | `get_dp_mapping_proposal(webi_doc_id: str, dp_id: str, target_datasource_id: str, strategies: Optional[str] = "SameID,SamePath,SameName", resolve_names: bool = True) -> Dict[str, Any]` | Simulates Change Data Source repointing and returns enriched object match statistics (`Ok`, `Ambiguous`, `NotFound`). |
| `change_dp_datasource` | **Tier 2** | `change_dp_datasource(webi_doc_id: str, dp_id: str, target_datasource_id: str, strategies: Optional[str] = "SameID,SamePath,SameName", custom_mappings: Optional[List[Dict[str, str]]] = None, save: bool = True) -> Dict[str, Any]` | Executes Change Data Source repointing on a Data Provider and optionally saves in-place. **Requires confirmation.** |
