---
type: troubleshooting_runbook
title: "IES 10901: Database Connectivity & Handshake Failure"
description: Root cause analysis and step-by-step triage runbook for SAP BusinessObjects error IES 10901 (Cannot connect to the relational database).
status: active
last_updated: 2026-11-06
tags:
  - ies-10901
  - connectivity
  - idt
  - network
  - troubleshooting
related:
  - ./index.md
  - ../sap_bo/connections_and_idt.md
  - ../tools/catalog_schedules_and_diagnostics.md
  - ./ora_01017_and_db_auth.md
---

# IES 10901: Database Connectivity & Handshake Failure

## 1. Error Signature & Meaning

- **Error Code:** `IES 10901` (often paired with driver messages such as `Connection refused`, `SocketTimeoutException`, `ORA-12154`, or `TNS-12541: TNS:no listener`).
- **Subsystem:** Web Intelligence Processing Server / Connection Server (64-bit) / Adaptive Job Server.
- **Meaning:** The SAP BusinessObjects processing tier failed to establish a network or driver handshake with the target relational database defined in the Universe connection.

---

## 2. Ranked Probable Causes

1. **Rank 1 (High Probability) — Network Routing, Firewall, or DB Listener Outage:**
   The target RDBMS listener is down for maintenance/backup, or a firewall rule blocks traffic between the SAP BO processing node and the database host/port.
2. **Rank 2 (Medium Probability) — Misconfigured 64-Bit RDBMS Client Driver on BO Node:**
   Missing or mismatched `tnsnames.ora` entry, ODBC DSN, or JDBC driver `.sbo`/`.prm` configuration on one or more nodes in the SAP BO cluster.
3. **Rank 3 (Lower Probability) — Stale Connection Pool or Corrupt `.cns` Definition:**
   The secured relational connection in the CMS points to a decommissioned database hostname or port.

---

## 3. Step-by-Step Remediation Protocol

### Step 1: Identify the Impacted Universe & Connection via `bo-mcp`
1. Call [`get_dp(webi_doc_id)`](../tools/catalog_semantic_and_webi.md) and [`get_dp_details(webi_doc_id, dp_id)`](../tools/catalog_semantic_and_webi.md) to retrieve `dataSourceId` (Universe ID).
2. Call [`get_universe_connection_id(universe_id)`](../tools/catalog_semantic_and_webi.md) to obtain the `CCIS.DataConnection` ID.

### Step 2: OS & Network Layer Verification (On the SAP BO Server Host)
From the OS shell of the server running the **Adaptive Job Server** and **Web Intelligence Processing Server**:
- Test TCP reachability to the database host and port:
  ```bash
  nc -zv <db_host> <db_port>
  # or
  telnet <db_host> <db_port>
  ```
- For Oracle connections, verify TNS resolution using the 64-bit Oracle client installed on the BO node:
  ```bash
  tnsping <TNS_ALIAS>
  ```

### Step 3: Semantic Layer Connection Test (Strictly via IDT / UDT)
> [!IMPORTANT]
> **Do NOT instruct administrators to test the relational connection in the Central Management Console (CMC).** The CMC does not have a "Test Connection" button for relational connections. See [Relational Connections & IDT Testing Rules](../sap_bo/connections_and_idt.md).

1. Launch **Information Design Tool (IDT)** (for `.unx` universes) or **Universe Design Tool (UDT)** (for legacy `.unv` universes).
2. Connect to the CMS Repository via **Repository Resources**.
3. Open the relational connection (`.cns` or `.cnx`) and click **Test Connection**.
4. Verify both **Local** and **Server** middleware modes if applicable, update host/port parameters if changed, and re-publish the connection to the repository.
