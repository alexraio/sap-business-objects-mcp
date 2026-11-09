# LLM-Wiki Chronological Log (`wiki/log.md`)

This file is an append-only timeline tracking all `ingest`, `update`, and `lint` operations performed on the `wiki/` bundle.

---

## [2026-11-09] update | Co-Located Remote MCP Server, Local Log Analyzer & ODBC Auditing Design
- **Source:** Interactive `/brainstorming` architectural validation session
- **Updated Pages:** `wiki/architecture/remote_sse_roadmap.md`, `wiki/architecture/index.md`, `wiki/index.md`, `TODO.md`
- **Summary:** Documented the validated architectural design and Decision Log (`D1`–`D4`) for running `bo-mcp` natively on the SAP BusinessObjects host (Linux `systemd` / Windows Service) over `Streamable HTTP`/`SSE` with multi-tenant RBAC (`is_admin`), pure-Python reverse-streaming `.glf` log analysis (`LogService`), and RDBMS-agnostic `pyodbc` Auditing DB introspection (`AuditService`).

---

## [2026-11-06] refactor | Consolidate All Wiki Assets under `wiki/`
- **Source:** Repository structure optimization
- **Updated Pages:** `wiki/index.md`, `wiki/log.md`, `wiki/raw/README.md`, `wiki/*/index.md`, `.agents/rules/wiki_operations.md`, `AGENTS.md`, `README.md`
- **Summary:** Clustered all LLM-Wiki folders (`architecture/`, `sap_bo/`, `tools/`, `troubleshooting/`, `raw/`) and migrated legacy `docs/*.md` into `wiki/raw/design_notes/` inside a single self-contained `wiki/` root directory.

---

## [2026-11-06] init & ingest | Initial LLM-Wiki & OKF Bundle Compilation
- **Sources:**
  - `wiki/raw/design_notes/enterprise_authentication_and_session_design.md`
  - `wiki/raw/design_notes/intelligent_diagnostics_agent_design.md`
  - `.agents/skills/sap-business-objects/SKILL.md`
  - `.agents/skills/sap-business-objects/references/*.md`
  - `TODO.md`, `server.py`, `core/*.py`, `services/*.py`
- **Created Pages:**
  - Root: `wiki/index.md`, `wiki/log.md`, `wiki/raw/README.md`, `.agents/rules/wiki_operations.md`
  - Architecture: `wiki/architecture/index.md`, `system_overview.md`, `authentication_and_sessions.md`, `intelligent_diagnostics_engine.md`, `remote_sse_roadmap.md`
  - SAP BO Domain: `wiki/sap_bo/index.md`, `cms_query_language.md`, `connections_and_idt.md`, `semantic_layer_and_universes.md`, `webi_raylight_lifecycle.md`
  - MCP Tools: `wiki/tools/index.md`, `catalog_semantic_and_webi.md`, `catalog_cms_admin_and_infostore.md`, `catalog_schedules_and_diagnostics.md`
  - Troubleshooting: `wiki/troubleshooting/index.md`, `ies_10901_database_connectivity.md`, `wis_30553_webi_processing_timeout.md`, `ora_01017_and_db_auth.md`, `wsr_00400_and_session_expiry.md`
- **Summary:** Bootstrapped the project's persistent LLM-Wiki combining Andrej Karpathy's `llm-wiki` pattern and Google Cloud's Open Knowledge Format (OKF). Consolidated all architectural specifications, SAP BusinessObjects 4.3 SP5 domain rules, 43 MCP tool contracts, Change Data Source strategies, in-session export workflows, and error triage runbooks into an interconnected Markdown graph.
