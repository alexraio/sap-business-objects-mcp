---
type: sap_domain
title: Web Intelligence & Raylight REST Lifecycle
description: Comprehensive technical reference for the SAP BusinessObjects Web Intelligence Raylight REST API (/raylight/v1), in-memory session state, prompts, dataset extraction, and binary exports.
status: active
last_updated: 2026-11-06
tags:
  - webi
  - raylight
  - prompts
  - export
  - dataset
related:
  - ./index.md
  - ./semantic_layer_and_universes.md
  - ../tools/catalog_semantic_and_webi.md
  - ../troubleshooting/wis_30553_webi_processing_timeout.md
---

# Web Intelligence & Raylight REST Lifecycle

The **Raylight RESTful Web Services** (`/biprws/raylight/v1`) provide programmatic control over Web Intelligence (`.wid`) documents hosted by the **Web Intelligence Processing Server**.

---

## 1. In-Memory Document Session State

Understanding how Raylight manages document state is essential for reliable data extraction and exporting:

1. **Repository State vs. Working Session State:**
   When a document is opened or queried via `/raylight/v1/documents/{docId}`, the Web Intelligence Processing Server loads a working copy into an **in-memory document session** tied to the caller's `X-SAP-LogonToken`.
2. **Purged Documents & Static Cache:**
   Enterprise report templates are frequently saved in the CMS with **purged Data Providers** (to minimize `.wid` file size on the Input FRS and enforce row-level security on open). Reading or exporting a purged template without refreshing first yields empty tables or header-only structures.
3. **In-Session Refresh (`PUT /documents/{docId}/parameters?refresh=true`):**
   Refreshing the document populates the in-memory microcube for the active `X-SAP-LogonToken` session. Subsequent calls in the same session (such as `get_report_element_data` or `export_webi_doc`) read directly from that freshly populated microcube without needing to overwrite the master template in the CMS repository.
4. **Persisting Changes (`PUT /documents/{docId}`):**
   Changes made in memory (refreshed microcubes, changed data sources, new variables) remain transient until `save_webi_doc` commits them to the CMS.

---

## 2. Prompts, Parameters & List of Values (LOV)

1. **Inspecting Parameters (`GET /documents/{docId}/parameters`):**
   Returns prompt definitions including `id` (integer index), `name` (prompt text), `technicalName`, `type`, `cardinality` (`Single`, `Multiple`, `Interval`), `optional` boolean, and `constrained` boolean.
2. **Fetching Allowed Values (`GET /documents/{docId}/parameters/{paramId}/values`):**
   For constrained prompts, returns the paginated List of Values (LOV).
3. **Submitting Answers & Refreshing (`PUT /documents/{docId}/parameters?refresh=true`):**
   Raylight expects single values as a dict `{"$": "val"}` and multiple values as a list `[{"$": "v1"}, {"$": "v2"}]` inside `answer.values.value`. `WebiService.refresh_webi_doc` normalizes both single strings and Python lists automatically.

---

## 3. Defensive Tabular Data Extraction (`/dataset` vs. `/data`)

To prevent LLM context window overflow, tabular extraction follows a 3-step progressive funnel:

```
get_reports(doc_id) ──> get_report_elements(doc_id, rep_id) ──> get_report_element_data(doc_id, rep_id, elem_id, max_rows=1000)
```

- **Endpoint Resolution:** `WebiService.get_report_element_data` queries `GET /documents/{docId}/reports/{repId}/elements/{elemId}/dataset` (the structured JSON dataset endpoint in SAP BO 4.3) and automatically falls back to `/data` if needed.
- **Non-Tabular Layout Elements:** Elements of type `Cell`, `PageZone`, or decorative containers do not expose a tabular dataset; `WebiService` catches the exception and returns an informative `note` explaining that the element is a layout container rather than a data table (`VTable`, `HTable`, `XTable`, `Visualization`).

---

## 4. Content-Negotiated Binary Exports (`PDF`, `XLSX`, `CSV`)

Raylight streams binary document exports using the HTTP `Accept` header on standard document and report endpoints:

| Format | Scope | Raylight Endpoint | `Accept` MIME Header |
| :--- | :--- | :--- | :--- |
| **PDF** (`.pdf`) | Full Document | `GET /raylight/v1/documents/{docId}` | `application/pdf` |
| **PDF** (`.pdf`) | Single Tab | `GET /raylight/v1/documents/{docId}/reports/{repId}` | `application/pdf` |
| **Excel** (`.xlsx`) | Full Document | `GET /raylight/v1/documents/{docId}` | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| **Excel** (`.xlsx`) | Single Tab | `GET /raylight/v1/documents/{docId}/reports/{repId}` | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| **CSV** (`.csv`) | Single Tab* | `GET /raylight/v1/documents/{docId}/reports/{repId}` | `text/csv` |

*\*Note on CSV:* Raylight requires a specific `reportId` when exporting `text/csv` for report layout tabs. If `report_id` is omitted, [`export_webi_doc`](../tools/catalog_semantic_and_webi.md) automatically resolves the first report tab ID via `get_reports(doc_id)`. When `export_format="all"` and `refresh=True` are passed, the document is refreshed **once** at the start of the call and all three formats (`pdf`, `xlsx`, `csv`) are streamed from the same refreshed in-memory state.
