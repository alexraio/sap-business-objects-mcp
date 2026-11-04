---
name: sap-business-objects
description: >-
  Comprehensive guide and operational runbook for interacting with SAP BusinessObjects BI Platform 4.3 SP5
  using the bo-mcp server tools. Use when discovering or inspecting semantic universes (UNX/UNV), extracting
  Data Provider SQL queries, refreshing and exporting Web Intelligence documents (PDF, Excel, CSV), retrieving
  tabular block data, executing CMS SQL queries, auditing users/sessions, or diagnosing scheduled batch execution failures.
---

# SAP BusinessObjects Operational Skill (`bo-mcp`)

This skill guides AI agents in interacting efficiently, safely, and accurately with **SAP BusinessObjects BI Platform 4.3 SP5** REST Web Services (`biprws` and `raylight`) exposed through the `sap-business-objects` MCP server.

---

## 1. Core Operating Principles & Hard Rules

### 🚨 Mandatory Rule: Relational Connection Testing (CMC vs. IDT)
* **NEVER instruct users or administrators to test relational database connections in the Central Management Console (CMC).**
* In SAP BusinessObjects BI Platform 4.x, the CMC manages metadata, security, and folders for `CCIS.DataConnection` objects, but **does not possess a "Test Connection" button/feature**.
* **Relational connection testing (`.cnx` / `.cns`) is supported exclusively via Information Design Tool (IDT):**
  1. Open Information Design Tool (IDT).
  2. Connect to the CMS Repository via *Repository Resources*.
  3. Open the connection (`.cnx` or secured `.cns`) and click **Test Connection**.
* For legacy `.unv` connections, tests must be performed in **Universe Design Tool (UDT)**.

### 🛡️ Safe-by-Default Action Tiers
To prevent unintended data loss or administrative disruption, classify all tool operations:
* **Tier 1 (Safe & Read-Only - Autonomous Execution):**
  - Tool examples: `get_*`, `cms_query` (SELECT only), `diagnose_batch_failures`.
  - The agent executes these directly to fulfill user queries.
* **Tier 2 (State-Altering / Destructive - Explicit User Confirmation Mandatory):**
  - Tool examples: `delete_webi_doc`, `delete_instance`, `delete_folder`, `terminate_session`, `set_user_status`, `save_webi_doc`, `purge_dp`, `change_dp_datasource`.
  - **Required Protocol:** Before calling any Tier 2 tool, the agent **must pause**, present the target object details (Name, ID, parent folder/user, expected impact), and ask the user for explicit confirmation.

### 🧠 Context Window & Data Payload Defense
* Do **not** dump entire reports or execute unbounded queries.
* **Inspect Before Fetching:** Always call `get_report_elements` to discover block and table IDs before fetching raw table cells with `get_report_element_data`.
* **Bounded CMS Queries:** Always include specific projections (avoid `SELECT *`) and filter conditions (e.g., `WHERE SI_KIND = ...`, `TOP 50`).
* **Session Cleanliness:** Login is automatically handled using OS Keyring or `.env`. For long-running administrative tasks or after batch diagnostics, call `logout()` to release platform session resources.

---

## 2. Intent Routing Matrix

When a user request arrives, map the intent to the corresponding domain tools and consult the dedicated runbook in `references/`:

| User Goal / Intent | Primary MCP Tools | Reference Runbook |
| :--- | :--- | :--- |
| **Inspect Universes & Lineage** | `get_universes`, `get_universe_details`, `get_universe_structure`, `get_universe_related_reports`, `get_universe_connection_id` | [Semantic & Webi Runbook](./references/semantic_and_webi.md) |
| **Inspect Webi Documents & SQL** | `get_documents`, `get_webi_docs`, `get_doc_details`, `get_dp`, `get_dp_sql`, `get_dp_specification` | [Semantic & Webi Runbook](./references/semantic_and_webi.md) |
| **Refresh Reports & Answer Prompts** | `get_doc_parameters`, `get_parameter_lov`, `refresh_webi_doc`, `refresh_dp` | [Semantic & Webi Runbook](./references/semantic_and_webi.md) |
| **Extract Tabular Report Data** | `get_reports`, `get_report_elements`, `get_report_element_data`, `get_variables` | [Semantic & Webi Runbook](./references/semantic_and_webi.md) |
| **Export Reports (PDF, Excel, CSV)** | `export_webi_doc`, `get_reports` | [Semantic & Webi Runbook](./references/semantic_and_webi.md) |
| **CMS Metadata & Repository SQL** | `cms_query`, `get_folders`, `get_folder_details`, `get_categories` | [CMS Admin & Security](./references/cms_admin_and_security.md) |
| **Users, Groups & Session Audit** | `get_users`, `get_user_details`, `get_user_groups`, `get_group_users`, `get_active_sessions`, `terminate_session`, `set_user_status` | [CMS Admin & Security](./references/cms_admin_and_security.md) |
| **Batch Diagnostics & Failure RCA** | `diagnose_batch_failures`, `get_doc_schedules`, `get_doc_instances`, `get_instance_details` | [Batch Diagnostics & Schedules](./references/batch_diagnostics_and_schedules.md) |

---

## 3. Standard Execution Workflows

### Workflow A: Webi Inspection & Data Provider SQL Extraction
1. Search or list documents: `get_documents()` or `get_webi_docs(folder_id)`.
2. Inspect data providers: `get_dp(document_id)`.
3. Extract generated SQL: `get_dp_sql(document_id, dp_id)`.
4. Review the SQL query structure against the universe schema or database syntax.

### Workflow B: Safe Tabular Data Extraction
1. List tabs/sub-reports in the document: `get_reports(document_id)`.
2. List visualization and table blocks: `get_report_elements(document_id, report_id)`.
3. Locate the desired table block (filter by element type `Table`, `Form`, etc.).
4. Retrieve cell matrix: `get_report_element_data(document_id, report_id, element_id)`.

### Workflow C: CMS Metadata Querying
1. Identify target virtual table (`CI_INFOOBJECTS`, `CI_SYSTEMOBJECTS`, or `CI_APPOBJECTS`).
2. Construct targeted query with explicit fields:
   `SELECT SI_ID, SI_NAME, SI_KIND, SI_PARENTID FROM CI_INFOOBJECTS WHERE SI_KIND = 'Webi'`
3. Execute via `cms_query(query)`.

### Workflow D: Batch Schedule Failure Root Cause Analysis (RCA)
1. Trigger automated diagnostic scan: `diagnose_batch_failures(hours_back=24)`.
2. Review structured output: cluster signatures, error counts, ranked probable causes.
3. For specific failed reports, inspect recurring schedule rules: `get_doc_schedules(document_id)`.
4. If connectivity error is reported (`IES 10901`, `ORA-01017`), follow the IDT testing protocol outlined in [Batch Diagnostics](./references/batch_diagnostics_and_schedules.md).

### Workflow E: Webi Document Export (PDF, Excel, CSV)
1. **In-Session Refresh & Export (Recommended):** Pass `refresh=True` to refresh all data providers and stream the fresh data in a single atomic session:
   `export_webi_doc(document_id, export_format="all", refresh=True)`.
2. **Export Entire Document to PDF:** `export_webi_doc(document_id, export_format="pdf", refresh=True)`.
3. **Export to Excel Workbook:** `export_webi_doc(document_id, export_format="xlsx", refresh=True)`.
4. **Export Tab to CSV:** `export_webi_doc(document_id, export_format="csv", refresh=True)` (auto-resolves first tab if `report_id` omitted).
5. **Static Export (Without Refresh):** Omit `refresh` (or set `refresh=False`) to export the document as currently persisted in the CMS repository.

---

## 4. Verification and Error Handling

* **`WSR 00400` / Invalid Token:** Session expired. Call `login()` to renew `X-SAP-LogonToken`.
* **`IES 10901` (Cannot connect to database):**
  - Check host network routing from the SAP BO server.
  - Test relational database connectivity via **Information Design Tool (IDT)**, NOT CMC.
* **`WIS 30553` (Webi Processing Server memory/timeout):**
  - Check document complexity, formula recursions, or server sizing in CMC Server administration.
* **Zero Results on CMS Query:**
  - Verify casing and quotes. CMS SQL strings use single quotes `'...'`.
  - CMS SQL does not support `JOIN` or `GROUP BY`.

