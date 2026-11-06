# Agent Guidelines & Repository Rules

For comprehensive rules, refer to:
- **Project & Domain Rules:** [.agents/rules/project_rules.md](file:///.agents/rules/project_rules.md)
- **LLM-Wiki & OKF Operations:** [.agents/rules/wiki_operations.md](file:///.agents/rules/wiki_operations.md)
- **Project Knowledge Wiki (OKF Entry Point):** [wiki/index.md](file:///wiki/index.md)

## Key Directives:

1. **Primary Language:**
   - All source code, docstrings, technical documentation, architectural designs, wiki pages, commit messages, and repository rules must be written in **English**.
   - Conversational responses to the user should match the user's language (e.g. Italian), but all committed files and artifacts must be in English.

2. **SAP BusinessObjects Connection Testing:**
   - In SAP BO 4.x, the Central Management Console (CMC) does **not** provide a "Test Connection" function for relational connections.
   - Relational connection testing (`.cns` / `.cnx` for UNX) is supported exclusively through the **Information Design Tool (IDT)** (or Universe Design Tool for legacy `.unv`).
   - Never instruct administrators or users to test database connectivity within the CMC.

3. **LLM-Wiki Navigation (`wiki/`):**
   - Start technical lookups and domain verification by reading [`wiki/index.md`](file:///wiki/index.md) via progressive disclosure.
   - Keep raw, unmodified reference dumps in [`wiki/raw/`](file:///wiki/raw/README.md) and maintain synthesized, YAML-frontmatter-annotated concept pages in [`wiki/`](file:///wiki/index.md).
