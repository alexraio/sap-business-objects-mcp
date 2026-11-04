# Project Rules & Guidelines

## 1. Primary Language
- **English as Primary Project Language:** All project source code, docstrings, variable/function names, commit messages, technical documentation, architectural specifications, and agent rules must be authored in **English**.
- Even when the user interacts or asks questions in Italian, code changes, repository documentation, comments, and project rules must remain strictly in English (conversational chat responses to the user may remain in Italian to match the user's language).

## 2. SAP BusinessObjects Connection Testing (CMC vs IDT)
- **NEVER instruct users to test relational connections in CMC:** In SAP BusinessObjects BI Platform 4.x, the Central Management Console (CMC) manages metadata, access rights, and folders for `CCIS.DataConnection` objects, but **does NOT have a "Test Connection" button/feature**.
- **Always specify Information Design Tool (IDT):** Testing relational database connectivity, credentials, and network handshake for UNX universes (`.cnx` / `.cns`) must strictly be performed via the **Information Design Tool (IDT)**:
  1. Launch Information Design Tool (IDT).
  2. Connect to the CMS Repository via *Repository Resources*.
  3. Open the relational connection (`.cnx` or secured `.cns`) and click **Test Connection**.
- **Legacy UNV Universes:** For legacy `.unv` connections, tests must be performed using **Universe Design Tool (UDT)**.

## 3. Root Cause Analysis (RCA) & Failure Diagnostics
- When diagnosing connection and execution failures (e.g. `IES 10901`, `Connection refused`, `ORA-01017`, `SocketTimeout`, `WIS 30553`):
  - Clearly distinguish **OS/Network checks** (e.g., `ping`, `nc -zv`, `telnet` from the host executing Adaptive Job Server / Webi Processing Server).
  - Clearly distinguish **Semantic Layer / Universe connection tests** (strictly via **IDT** or **UDT**).
  - Limit CMC guidance to operational administration (server statuses, job scheduling queues, log tracing levels, timeout limits).
