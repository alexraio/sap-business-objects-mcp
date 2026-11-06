---
type: troubleshooting_runbook
title: "WSR 00400, Session Expiry & FRS Storage Errors"
description: Runbook for handling expired X-SAP-LogonToken sessions (WSR 00400 / HTTP 401), File Repository Server errors (FWM 02024), and Publication bursting errors (FBE60502).
status: active
last_updated: 2026-11-06
tags:
  - wsr-00400
  - fwm-02024
  - fbe-60502
  - session
  - frs
related:
  - ./index.md
  - ../architecture/authentication_and_sessions.md
  - ../tools/catalog_semantic_and_webi.md
---

# WSR 00400, Session Expiry & FRS Storage Errors

## 1. `WSR 00400` / `HTTP 401`: Expired or Invalid Session Token

### Meaning
The `X-SAP-LogonToken` held by `BOEClient` has timed out on the Web Application Container Server (WACS) / Tomcat REST gateway, or the session was terminated by an administrator.

### Remediation
1. Invoke the [`login()`](../tools/catalog_semantic_and_webi.md) MCP tool to acquire a fresh `X-SAP-LogonToken`.
2. **Implementation Safeguard (`core/client.py`):** When `BOEClient._get_auth_template()` calls `GET /biprws/logon/long`, it explicitly strips any existing `X-SAP-LogonToken` header from the request. Sending an expired token header to `/logon/long` causes WACS to reject the template request with `HTTP 401` before authentication can even occur.

---

## 2. `FWM 02024`: File Repository Server (FRS) Storage or Access Error

### Meaning
The **Input File Repository Server (Input FRS)** or **Output File Repository Server (Output FRS)** failed to read a report template (`.wid`) or write a generated scheduled instance (`.wid`, `.pdf`, `.xlsx`) to the physical filestore disk.

### Remediation
1. **Disk Space Check:** Verify free disk space and inode availability on the shared NAS/SAN mount hosting the SAP BO `FileStore/Input` and `FileStore/Output` directories.
2. **OS Service Account Permissions:** Verify that the OS user running the SIA (Server Intelligence Agent) has read/write permissions on the FRS mount.
3. **Orphan Consistency Check:** Run the **Repository Diagnostic Tool (RDT)** if CMS metadata references an FRS file that was manually deleted from disk.

---

## 3. `FBE60502`: Publication Bursting & Dynamic Recipient Error

### Meaning
A scheduled **Publication** (`SI_KIND = 'Publication'`) failed while resolving its Dynamic Recipients Data Provider or applying personalization profile filters during report bursting.

### Remediation
1. Open the Publication properties in BI Launchpad or CMC and verify the **Dynamic Recipients** source report.
2. Open the Dynamic Recipients Webi report and refresh it interactively (or via [`refresh_webi_doc`](../tools/catalog_semantic_and_webi.md)) to ensure the recipient ID and email columns return valid, non-null rows.
3. Verify that SMTP / destination server settings are enabled and reachable on the **Adaptive Job Server (Destination Job Service)**.
