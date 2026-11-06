---
type: architecture
title: Remote HTTP / SSE Deployment Roadmap
description: Architectural roadmap for evolving the SAP BusinessObjects MCP server from local STDIO execution to a multi-tenant HTTP/SSE/Streamable-HTTP gateway.
status: draft
last_updated: 2026-11-06
tags:
  - roadmap
  - sse
  - streamable-http
  - multi-tenancy
related:
  - ./index.md
  - ./system_overview.md
  - ./authentication_and_sessions.md
---

# Remote HTTP / SSE Deployment Roadmap

While `bo-mcp` runs over local `STDIO` by default, its internal architecture (`SessionManager`, `UserSession`, and decoupled domain services) is pre-engineered for centralized network deployment using `SSE` or `Streamable HTTP`.

---

## 1. Completed Foundation

- **Decoupled Service Layer:** `services/*` and `BOEClient` have zero dependency on transport framing.
- **Thread-Safe Session Registry:** `core/session.py` (`SessionManager`) already isolates `UserSession` instances by `session_id` with `threading.RLock()` and TTL expiration.
- **FastMCP ASGI Support:** FastMCP 2.x natively bundles Starlette/Uvicorn for `sse` and `streamable-http` transports.

---

## 2. Planned Implementation Phases

### Phase 1: Dynamic FastMCP Context Binding
- Inject FastMCP `ctx: Context` into tool handlers (or via a `@with_session` decorator) to resolve `session_id = ctx.session_id` dynamically instead of using the `"default"` stdio session.

### Phase 2: Remote Credential & Token Ingestion
Because a remote server cannot read a client laptop's local OS Keyring, three enterprise patterns are supported:
1. **Per-Session `login` Tool Call:** Client invokes `login(username, password)` at session start; token binds to `ctx.session_id`.
2. **HTTP Header Pass-Through:** Client or gateway injects `X-SAP-LogonToken` or `Authorization` headers into the HTTP/SSE handshake.
3. **Enterprise SSO / Trusted Authentication Proxy:** An API Gateway (Kong, Envoy, Traefik) validates corporate SAML/OIDC identity and maps the user via SAP BO Trusted Authentication (`GET /biprws/logon/trusted` with `X-SAP-TRUSTED-USER`).

### Phase 3: Transport CLI & Network Hardening
- Add `--transport sse|streamable-http|stdio`, `--host`, and `--port` CLI flags and `MCP_TRANSPORT` / `MCP_PORT` environment variables.
- Enforce TLS termination, CORS origin allowlists, rate limiting, and `/health` readiness probes.
- Run a periodic background task invoking `session_manager.cleanup_expired_sessions()` every 5–10 minutes to prevent SAP BO session leaks.
