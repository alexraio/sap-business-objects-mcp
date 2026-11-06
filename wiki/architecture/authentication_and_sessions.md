---
type: architecture
title: Enterprise Authentication & Session Isolation
description: Design and implementation of multi-tier credential resolution (.env and OS Keyring), SecretStr memory protection, CLI onboarding, and per-session isolation.
status: active
last_updated: 2026-11-06
tags:
  - authentication
  - keyring
  - security
  - session-isolation
related:
  - ./index.md
  - ./system_overview.md
  - ./remote_sse_roadmap.md
  - ../troubleshooting/wsr_00400_and_session_expiry.md
---

# Enterprise Authentication & Session Isolation

The `bo-mcp` server implements a defense-in-depth authentication and session management architecture designed to eliminate plaintext password exposure while preserving SAP BusinessObjects user-level security profiles.

---

## 1. Design Principles & Non-Goals

- **Zero Plaintext Passwords in Memory or Logs:** Credentials are encapsulated in `AuthCredentials` using `pydantic.SecretStr` so that `repr()`, stack traces, and log statements mask passwords as `**********`.
- **No Interactive Prompts on MCP `stdin`:** Attempting `input()` or `getpass()` during active MCP execution corrupts the JSON-RPC stdio stream. Instead, interactive onboarding is isolated to a dedicated CLI command (`python server.py configure`).
- **Startup Resilience:** If credentials are missing when the MCP server starts, the server remains alive and returns actionable setup instructions when a tool is invoked rather than crashing with `sys.exit(1)`.
- **No Shared Superuser Account:** Every session binds to an explicit SAP BO user account so row-level security, folder permissions, and audit trails are honored.

---

## 2. Chained Credential Resolution (`core/auth/`)

`ChainedCredentialProvider` resolves credentials on-demand in strict priority order:

```
Priority 1: Environment Variables (.env / OS Env)
   ├── SAP_BO_REST_API_URL
   ├── SAP_BO_USERNAME
   └── SAP_BO_PASSWORD
          │
          ▼ (If incomplete or unset)
Priority 2: OS Native Keyring (service: "sap-business-objects-mcp")
   ├── macOS Keychain Access
   ├── Windows Credential Manager
   └── Linux SecretService / D-Bus (gracefully skipped on headless containers)
          │
          ▼ (If unconfigured)
Priority 3: Graceful Self-Service Guidance
   └── Tool returns instructions to run `python server.py configure`
```

### Interactive CLI Setup Wizard (`core/auth/cli.py`)
Administrators and analysts can manage OS Keyring credentials from their terminal:
- `python server.py configure` — Prompts for REST API URL, username, and masked password (`getpass`), with optional immediate live logon verification.
- `python server.py status` — Reports active credential source without exposing secrets.
- `python server.py test` — Tests live connectivity against `GET/POST /biprws/logon/long`.
- `python server.py clear` — Purges stored credentials from the OS Keyring.

---

## 3. Manual OS Keyring Provisioning

Enterprise IT teams can also provision credentials directly via native OS tools under the service name **`sap-business-objects-mcp`**:

- **macOS (Keychain Access):** Create a new password item with *Keychain Item Name* `sap-business-objects-mcp` and *Account Name* set to the SAP BO username.
- **Windows (Credential Manager):** Add a generic Windows credential with *Internet or network address* `sap-business-objects-mcp`.
- **Linux (`secret-tool`):**
  ```bash
  secret-tool store --label="SAP BO MCP" service sap-business-objects-mcp username <sap-username>
  ```

---

## 4. Session Isolation (`core/session.py`)

`SessionManager` maps each `session_id` to an independent `UserSession`:
- Each `UserSession` owns a dedicated `BOESDKParser` and `BOEClient` instance, complete with its own `requests.Session` cookie jar and `X-SAP-LogonToken` header.
- Tracks `created_at`, `last_accessed`, and `ttl_seconds` (default 3600s).
- `cleanup_expired_sessions()` automatically invokes `bo_logoff()` on expired sessions to release SAP BusinessObjects concurrent license seats on the Central Management Server.
