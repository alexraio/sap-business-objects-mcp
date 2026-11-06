---
type: troubleshooting_runbook
title: "ORA-01017 & Database Authentication Failures"
description: Triage and credential rotation runbook for RDBMS authentication failures (ORA-01017, ORA-28000, Login failed) in SAP BusinessObjects.
status: active
last_updated: 2026-11-06
tags:
  - ora-01017
  - ora-28000
  - credentials
  - idt
  - troubleshooting
related:
  - ./index.md
  - ./ies_10901_database_connectivity.md
  - ../sap_bo/connections_and_idt.md
---

# ORA-01017 & Database Authentication Failures

## 1. Error Signatures & Meaning

- **`ORA-01017: invalid username/password; logon denied`** (Oracle)
- **`ORA-28000: the account is locked`** (Oracle)
- **`Login failed for user '<username>'`** (Microsoft SQL Server)
- **`authentication failed`** (SAP HANA / PostgreSQL / Snowflake)

**Meaning:** Network connectivity to the database server succeeded, but the RDBMS rejected the credentials configured in the SAP BusinessObjects relational connection.

---

## 2. Ranked Probable Causes

1. **Rank 1 — Expired or Rotated Database Service Account Password:**
   The technical database password was rotated by DBAs without updating the corresponding `.cns` connection in SAP BusinessObjects.
2. **Rank 2 — Account Locked by Failed Retry Storm (`ORA-28000`):**
   Dozens of scheduled nocturnal Webi reports attempted to run using an outdated password, triggering the database's failed-login lockout policy.
3. **Rank 3 — SSO / Database Credential Mapping Failure:**
   If the connection is configured to use *Database Credentials Mapped to SAP BO User* rather than a shared technical account, the individual user's DB credential mapping in CMC User Properties is missing or expired.

---

## 3. Step-by-Step Remediation Protocol

### Step 1: Prevent Lockout Amplification
1. Coordinate with the DBA team to unlock the database service account (`ALTER USER <user> ACCOUNT UNLOCK;`).
2. Before unlocking, pause active retries if a batch storm is in progress.

### Step 2: Update & Test Credentials in Information Design Tool (IDT)
> [!IMPORTANT]
> Relational connection credentials for `.unx` universes must be tested and republished via **Information Design Tool (IDT)** (or **UDT** for `.unv`), never tested in the CMC. See [Relational Connections & IDT Testing Rules](../sap_bo/connections_and_idt.md).

1. Launch **Information Design Tool (IDT)** and connect to the CMS Repository via **Repository Resources**.
2. Locate the secured connection (`.cns`) under `/Connections` (use [`get_universe_connection_id`](../tools/catalog_semantic_and_webi.md) to find the exact connection ID/name).
3. Edit the connection parameters and enter the updated database username and password.
4. Click **Test Connection** in IDT and confirm a successful handshake.
5. Save and **Publish** the updated `.cns` connection to the CMS repository so all dependent UNX universes immediately inherit the new credentials.
