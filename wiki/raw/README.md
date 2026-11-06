# Raw Knowledge Sources (`wiki/raw/`)

This directory serves as the **immutable source layer** inside the [`wiki/`](../index.md) folder, following Andrej Karpathy's **LLM-Wiki** architecture.

## Purpose & Rules

1. **Read-Only for AI Agents:**
   - Files placed in `wiki/raw/` are primary source materials (SAP BusinessObjects REST API documentation excerpts, SAP Notes / KBAs, raw error trace dumps, RFC drafts, or original design specifications).
   - AI agents **read** from `wiki/raw/` during the **Ingest** operation to synthesize and update structured pages inside [`wiki/`](../index.md), but **never modify or delete** files in `wiki/raw/`.

2. **Subdirectories:**
   - [`design_notes/`](./design_notes/) — Original architectural RFCs and design documents:
     - [`enterprise_authentication_and_session_design.md`](./design_notes/enterprise_authentication_and_session_design.md)
     - [`intelligent_diagnostics_agent_design.md`](./design_notes/intelligent_diagnostics_agent_design.md)
   - `sap_docs/` — Official SAP BusinessObjects 4.3 SP5 RESTful Web Services (`biprws`, `raylight`, `sl`) documentation snippets.
   - `sap_notes/` — SAP Knowledge Base Articles (KBAs) and OSS Notes.
   - `error_dumps/` — Anonymized JSON/XML error payloads, `SI_STATUSINFO` dumps, and server trace logs.

3. **How to Ingest a New Source:**
   Drop a file into `wiki/raw/` and instruct the agent:
   > *"Ingest `wiki/raw/<filename>` into the wiki."*

   Refer to [`.agents/rules/wiki_operations.md`](../../.agents/rules/wiki_operations.md) for the complete ingestion and maintenance protocol.
