---
type: sap_domain
title: Relational Connections & IDT Testing Rules
description: Architecture of SAP BusinessObjects relational database connections (.cnx, .cns, .unv) and mandatory operational rules for testing connectivity in IDT and UDT.
status: active
last_updated: 2026-11-06
tags:
  - connections
  - idt
  - udt
  - cmc
  - mandatory-rule
related:
  - ./index.md
  - ./semantic_layer_and_universes.md
  - ../troubleshooting/ies_10901_database_connectivity.md
  - ../troubleshooting/ora_01017_and_db_auth.md
---

# Relational Connections & IDT Testing Rules

In SAP BusinessObjects BI Platform 4.3 SP5, relational database connections (`SI_KIND = 'CCIS.DataConnection'`) bridge the Semantic Layer (`.unx` / `.unv` universes) and the underlying corporate RDBMS (Oracle, SQL Server, SAP HANA, PostgreSQL, Snowflake, Teradata).

---

## 1. Mandatory Operational Directive: CMC vs. IDT

> [!CAUTION]
> **NEVER instruct users or administrators to test relational database connections in the Central Management Console (CMC).**
>
> In SAP BusinessObjects BI Platform 4.x, the web-based CMC allows administrators to view connection metadata, organize connection folders, and assign user/group access rights, but **it does NOT provide a "Test Connection" button or diagnostic action for relational connections (`CCIS.DataConnection`)**.

### Correct Connection Testing Tools by Universe Type

| Universe / Connection Format | Required Client Tool | Step-by-Step Connection Test Procedure |
| :--- | :--- | :--- |
| **UNX Universe** (`DSL.MetaDataFile`)<br>Secured Connection (`.cns`) or Local (`.cnx`) | **Information Design Tool (IDT)** | 1. Launch **Information Design Tool (IDT)**.<br>2. Open **Repository Resources** and log in to the CMS.<br>3. Navigate to `/Connections` and open the target `.cns` connection.<br>4. Click **Test Connection** to validate the 64-bit driver and server handshake. |
| **Legacy UNV Universe** (`Universe`) | **Universe Design Tool (UDT)** | 1. Launch **Universe Design Tool (UDT)**.<br>2. Import the `.unv` universe or open **Tools $\rightarrow$ Connections**.<br>3. Select the relational connection and click **Test**. |

---

## 2. Two-Tier Connectivity Diagnostics (OS vs. Semantic Layer)

Because a connection test in IDT can execute either locally (from the designer workstation) or via the BI server (Connection Server), troubleshooting database failures such as [`IES 10901`](../troubleshooting/ies_10901_database_connectivity.md) or [`ORA-01017`](../troubleshooting/ora_01017_and_db_auth.md) requires separating checks into three distinct layers:

1. **OS & Network Layer (BI Server Node):**
   - Verify that the host running the **Web Intelligence Processing Server** and **Adaptive Job Server** can reach the database IP and port (`ping`, `nc -zv <db_host> <db_port>`, `telnet`, or `tnsping` for Oracle).
   - Verify that 64-bit RDBMS client middleware (`tnsnames.ora`, ODBC DSNs, JDBC `.sbo`/`.prm` configurations) is installed on every processing node in the SAP BO cluster.
2. **Semantic Layer / Credentials (IDT / UDT):**
   - Validate database credentials, connection pool parameters, and driver handshake strictly within **IDT** (for `.cns`/`.cnx`) or **UDT** (for `.unv`).
   - If credentials were updated in a local project, always **Publish Connection to a Repository** to update the secured `.cns` object in `CI_APPOBJECTS`.
3. **Platform Administration Layer (CMC):**
   - Use the CMC exclusively for inspecting **Connection Server (64-bit)** / **Adaptive Processing Server (Data Federation Service)** running states, trace log levels, and access control lists (ACLs) on the connection object.

---

## 3. Discovering Connection Lineage via `bo-mcp`

To identify which relational connection powers a specific universe or report:
1. Find the universe ID associated with a Webi Data Provider using `get_dp_details(webi_doc_id, dp_id)`.
2. Retrieve the connection ID linked to that universe using [`get_universe_connection_id(universe_id)`](../tools/catalog_semantic_and_webi.md).
3. Query full connection metadata in `CI_APPOBJECTS` via [`cms_query`](../tools/catalog_cms_admin_and_infostore.md):
   ```sql
   SELECT SI_ID, SI_NAME, SI_CUID, SI_DESCRIPTION, SI_UPDATE_TS
   FROM CI_APPOBJECTS
   WHERE SI_ID = <connection_id>
   ```
