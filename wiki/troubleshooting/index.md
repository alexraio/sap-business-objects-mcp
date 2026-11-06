---
type: index
title: Troubleshooting & SAP BO Error Runbooks Index
description: Navigation index for SAP BusinessObjects error code diagnostics, Root Cause Analysis (RCA) procedures, and administrator remediation guides.
status: active
last_updated: 2026-11-06
tags:
  - troubleshooting
  - error-codes
  - rca
  - index
related:
  - ../index.md
  - ./ies_10901_database_connectivity.md
  - ./wis_30553_webi_processing_timeout.md
  - ./ora_01017_and_db_auth.md
  - ./wsr_00400_and_session_expiry.md
---

# Troubleshooting & Error Runbooks (`wiki/troubleshooting/`)

This section contains operational triage runbooks keyed by SAP BusinessObjects error codes encountered during interactive execution or nocturnal batch schedules.

## Error Runbooks in this Section

| Runbook Page | Error Codes Covered | Primary Failure Category |
| :--- | :--- | :--- |
| [IES 10901: Database Connectivity & Handshake Failure](./ies_10901_database_connectivity.md) | `IES 10901`, `SocketTimeout`, `Connection refused`, `TNS-12541` | `NETWORK_TIMEOUT` / Relational Driver |
| [WIS 30553 / WSR 00999: Webi Processing Server Timeout & OOM](./wis_30553_webi_processing_timeout.md) | `WIS 30553`, `WIS 30551`, `ERR_WIS_30270`, `WSR 00999` | `SERVER_RESOURCE_OOM` / Calculation Timeout |
| [ORA-01017 & Database Authentication Failures](./ora_01017_and_db_auth.md) | `ORA-01017`, `ORA-28000`, `Login failed for user` | `AUTH_CREDENTIALS` |
| [WSR 00400, Session Expiry & FRS Storage Errors](./wsr_00400_and_session_expiry.md) | `WSR 00400`, `HTTP 401`, `FWM 02024`, `FBE60502` | Session Lifecycle / FRS Storage / Bursting |

## Related Sections
- [Architecture & System Design](../architecture/index.md)
- [SAP BusinessObjects Domain Knowledge](../sap_bo/index.md)
- [MCP Tool Catalogs](../tools/index.md)
