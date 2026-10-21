# Agent Guidelines & Repository Rules

For comprehensive rules, refer to [.agents/rules/project_rules.md](file:///.agents/rules/project_rules.md).

## Key Directives:

1. **Primary Language:**
   - All source code, docstrings, technical documentation, architectural designs, commit messages, and repository rules must be written in **English**.
   - Conversational responses to the user should match the user's language (e.g. Italian), but all committed files and artifacts must be in English.

2. **SAP BusinessObjects Connection Testing:**
   - In SAP BO 4.x, the Central Management Console (CMC) does **not** provide a "Test Connection" function for relational connections.
   - Relational connection testing (`.cns` / `.cnx` for UNX) is supported exclusively through the **Information Design Tool (IDT)** (or Universe Design Tool for legacy `.unv`).
   - Never instruct administrators or users to test database connectivity within the CMC.
