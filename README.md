# SAP BusinessObjects MCP Server (`bo-mcp`)

[![FastMCP](https://img.shields.io/badge/FastMCP-2.13.1-blue.svg)](https://github.com/jlowin/fastmcp)
[![MCP](https://img.shields.io/badge/MCP-1.22.0-green.svg)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Package Manager](https://img.shields.io/badge/uv-package%20manager-purple.svg)](https://astral.sh/uv)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/alexraio/sap-business-objects-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/alexraio/sap-business-objects-mcp/actions/workflows/ci.yml)
[![SAP BO](https://img.shields.io/badge/SAP%20BusinessObjects-BI%204.3%20SP5-orange.svg)](https://www.sap.com)

A Model Context Protocol (**MCP**) server that exposes **SAP BusinessObjects BI Platform 4.3 SP5** administration, semantic analysis, Web Intelligence inspection, co-located `.glf` server log analysis, and direct ODBC Auditing Database introspection to AI coding assistants and autonomous agents. Built using **FastMCP 2.0** and the **SAP BI Platform REST Web Services (`biprws` and `raylight`)**, this server runs both **locally (`STDIO`)** and **remotely (`Streamable HTTP` / `SSE`)** on the SAP BusinessObjects host, enabling AI agents (such as **Google Antigravity IDE**, **Antigravity CLI `agy`**, Claude Desktop, and Cursor) to execute 56 specialized enterprise tools directly from natural language prompts.

---

## Table of Contents

- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
  - [1. Clone or Open the Repository](#1-clone-or-open-the-repository)
  - [2. Environment Configuration](#2-environment-configuration)
  - [3. Install Dependencies](#3-install-dependencies)
  - [4. Verify MCP Server Installation](#4-verify-mcp-server-installation)
- [Architecture & Deep Dive](#architecture--deep-dive)
  - [Modular Domain Services Architecture](#modular-domain-services-architecture)
  - [Directory Structure](#directory-structure)
  - [System Flow Diagram](#system-flow-diagram)
  - [Domain Services Breakdown](#domain-services-breakdown)
  - [Authentication & Session Lifecycle](#authentication--session-lifecycle)
- [Available MCP Tools Reference (56 Tools)](#available-mcp-tools-reference-56-tools)
  - [1. Authentication (2 Tools)](#1-authentication-2-tools)
  - [2. Universes & Semantic Layer (5 Tools)](#2-universes--semantic-layer-5-tools)
  - [3. Web Intelligence Documents & Lifecycle (5 Tools)](#3-web-intelligence-documents--lifecycle-5-tools)
  - [4. Webi Prompts, Parameters & Refresh (3 Tools)](#4-webi-prompts-parameters--refresh-3-tools)
  - [5. Webi Tabs, Blocks & Tabular Data (5 Tools)](#5-webi-tabs-blocks--tabular-data-5-tools)
  - [6. Data Providers, SQL & Change Data Source (8 Tools)](#6-data-providers-sql--change-data-source-8-tools)
  - [7. Central Management Server (CMS) Admin & Security (8 Tools)](#7-central-management-server-cms-admin--security-8-tools)
  - [8. Schedules & Instance Diagnostics (4 Tools)](#8-schedules--instance-diagnostics-4-tools)
  - [9. InfoStore, Folders & Categories (6 Tools)](#9-infostore-folders--categories-6-tools)
  - [10. Intelligent Diagnostics & Batch Health Monitoring (1 Tool)](#10-intelligent-diagnostics--batch-health-monitoring-1-tool)
  - [11. Local SAP BO Server Log Inspection — Admin-Only (3 Tools)](#11-local-sap-bo-server-log-inspection--admin-only-3-tools)
  - [12. Auditing Database ODBC Introspection — Admin-Only (4 Tools)](#12-auditing-database-odbc-introspection--admin-only-4-tools)
  - [13. MCP Server Self-Diagnostics & Remote Troubleshooting (1 Tool)](#13-mcp-server-self-diagnostics--remote-troubleshooting-1-tool)
- [Environment Variables](#environment-variables)
- [Co-Located Remote Deployment (Linux & Windows Server)](#co-located-remote-deployment-linux--windows-server)
- [Client Integration Guide](#client-integration-guide)
  - [1. Google Antigravity IDE](#1-google-antigravity-ide)
  - [2. Antigravity CLI (`agy`)](#2-antigravity-cli-agy)
  - [3. FastMCP Development Inspector (Web UI)](#3-fastmcp-development-inspector-web-ui)
  - [4. Claude Desktop & Other MCP Hosts](#4-claude-desktop--other-mcp-hosts)
- [Agent Skill: `sap-business-objects`](#agent-skill-sap-business-objects)
- [Available Scripts & Commands](#available-scripts--commands)
- [Testing & Verification](#testing--verification)
- [Contributing Guidelines](#contributing-guidelines)
- [Troubleshooting](#troubleshooting)
- [Security & Operational Best Practices](#security--operational-best-practices)
- [Author & License](#author--license)

---

## Key Features

- **Enterprise Authentication & Zero-Plaintext Security**: Interactive CLI credential intake with masked input (`getpass`), OS Keyring integration (**macOS Keychain**, **Windows Credential Manager**, **Linux SecretService**), and automatic account discovery. Eliminates plaintext passwords in `.env` files or LLM chat transcripts.
- **Session Isolation & Native SAP BO Security Rights**: Manages independent client sessions with dedicated `BOEClient` instances and `X-SAP-LogonToken` tokens, strictly preserving individual SAP BO user permissions, folder access, and universe row-level security.
- **Web Intelligence Execution & Data Extraction**: Retrieve prompts, query Allowed Values (LOV), answer prompts, trigger live document refresh, and extract tabular cell data from table and chart blocks without generating bloated binary files.
- **Data Provider SQL Inspection**: Extract the raw SQL query generated by the Semantic Layer for any Data Provider in a report.
- **Central Management Server (CMS) SQL Engine**: Execute arbitrary CMS SQL queries against `CI_INFOOBJECTS`, `CI_APPOBJECTS`, and `CI_SYSTEMOBJECTS` for deep platform introspection.
- **User & Security Administration**: List user accounts, inspect profile details, enable/disable accounts, list user groups, inspect group memberships, monitor active sessions, and terminate connections.
- **Semantic Layer & Universe Lineage**: Query UNX and UNV universes, inspect business classes/dimensions/measures, and map reports referencing each universe.
- **Schedule & Instance Diagnostics**: View scheduled execution rules, inspect instance history (*Success*, *Failed*, *Running*), and diagnose error messages of failed jobs.
- **Intelligent Diagnostics & Batch Health Monitoring**: Scan, cluster, and diagnose failed nocturnal batch executions (`SI_SCHEDULE_STATUS = 3`) for Web Intelligence reports and Publications (bursting). Normalizes error signatures and delivers Pydantic v2 structured reports with up to 3 ranked probable causes and actionable administrator remediation steps.
- **Repository Hierarchy Traversal**: Recursively traverse CMS folder trees and corporate categories.
- **Modular & Web-Ready**: Architecture decoupled into standalone domain services (`services/`), ready for native integration into a future FastAPI or Flask web application.

---

## Tech Stack

| Layer | Component | Version / Description |
| :--- | :--- | :--- |
| **Runtime** | Python | `>= 3.13` (Modern Python 3.13+ typing, dataclasses, pattern matching) |
| **Package Management** | Astral `uv` | Fast virtual environment & dependency management via `pyproject.toml` |
| **MCP Framework** | `fastmcp` | `2.13.1` (FastMCP 2.0 Generation 2, 48 registered tools) |
| **MCP Specification** | `mcp` | `1.22.0` (Standard Model Context Protocol) |
| **HTTP Engine** | `requests` | `2.32.5` persistent HTTP keep-alive session with custom timeout |
| **Security & Secrets** | `keyring` | `25.7.0` (Native OS Keychain / Credential Manager integration) |
| **Platform Paths** | `platformdirs` | `4.5.0` (Standard OS user config & cache directories) |
| **Data Validation** | `pydantic` | `2.12.5` (Strict schema validation and structured diagnostic models) |
| **Configuration** | `python-dotenv` | `1.2.1` for loading `.env` configuration relative to script location |
| **Target Platform** | SAP BusinessObjects BI | BI 4.3 SP5 (Support Package 5) REST Web Services (`biprws` and `raylight`) |



---

## Prerequisites

1. **Python 3.13+**: Verified with Python 3.13.0+.
2. **`uv` Package Manager** (recommended) or standard `pip` + `python3 -m venv`.
   - Install `uv` on macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Or via Homebrew: `brew install uv`
3. **Network Access to SAP BusinessObjects 4.3 SP5**:
   - Access to your SAP BI Platform REST Web Services URL (typically `http://<host>:<port>/biprws`).
   - A valid SAP BusinessObjects user account (e.g. Enterprise, LDAP, or WinAD) with rights to query the CMS and access Web Intelligence documents.

---

## Getting Started

### 1. Clone or Open the Repository

```bash
git clone https://github.com/your-username/BO_MCP.git
cd BO_MCP
```

### 2. Authentication Configuration

The MCP server supports two credential methods, resolved by priority:

#### Option A (Recommended for Enterprise): Secure OS Keyring (Zero-Plaintext)

Store credentials directly in your operating system's native encrypted keychain (**macOS Keychain**, **Windows Credential Manager**, or **Linux SecretService**). Passwords are never written to disk in plaintext or logged.

1. Run the interactive configuration wizard:
   ```bash
   python server.py configure
   ```
   *(Prompts for API URL, Username, and Password with masked input via `getpass`)*

2. Manage or test stored credentials:
   ```bash
   python server.py status    # Check active resolved credentials
   python server.py test      # Test stored credentials against the live SAP BO server
   python server.py clear     # Remove credentials from the OS Keyring
   ```

3. **Manual OS Keyring Configuration (No Python/CLI required)**:
   You or your IT administrator can also add the credential directly in the OS GUI:
   - **macOS (Keychain Access)**: Add a new generic password item with service `sap-business-objects-mcp`, your SAP username, and password.
   - **Windows (Credential Manager)**: Under *Windows Credentials -> Add a generic credential*, specify Internet or network address `sap-business-objects-mcp`, your username, and password.
   - **Linux (Seahorse / SecretService)**: Add an item under default keyring with service `sap-business-objects-mcp`.

4. **OS Keyring Account Auto-Discovery**:
   If credentials are saved in the OS Keyring, you do **not** need to store your username in configuration files. If `SAP_BO_USERNAME` is omitted from `.env` or client configuration, the server automatically discovers the active account name directly from the OS Keyring. You only need to define `SAP_BO_REST_API_URL`.


#### Option B (Development / Testing): Local `.env` File

For local development or automated CI/CD pipelines, you can provide credentials via `.env`:

```bash
cp .env.example .env
```

```env
# SAP BusinessObjects REST API Configuration (BI 4.3 SP5)
SAP_BO_REST_API_URL="http://your-bo-host:8080/biprws"

# Authentication Credentials (Priority 1 if defined)
SAP_BO_USERNAME="Administrator"
SAP_BO_PASSWORD="YourPasswordHere"
```

> [!IMPORTANT]
> - **Resolution Priority:** If `.env` contains credentials, they take precedence (Priority 1). If `.env` is absent or incomplete, the server automatically reads from the secure OS Keyring (Priority 2).
> - If no credentials exist anywhere, the server starts cleanly without crashing and guides the user via tool response messages to run `python server.py configure`.


### 3. Install Dependencies

Using `uv` (recommended):

```bash
uv sync
```

Alternatively, using standard `pip`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Verify MCP Server Installation

Run FastMCP inspection to verify that all 48 tools are registered:

```bash
uv run fastmcp inspect server.py
```

Expected output:

```text
Server
  Name:         SAP Business Objects
  Version:      2.13.1
  Generation:   2

Components
  Tools:        48
  Prompts:      0
  Resources:    0
  Templates:    0

Environment
  FastMCP:      2.13.1
  MCP:          1.22.0
```

---

## Architecture & Deep Dive

### Modular Domain Services Architecture

The codebase follows a clean, domain-driven service architecture. Business logic is separated into independent services, making each module testable in isolation and ready to be imported into a future Web API (e.g., FastAPI) without modifying FastMCP.

```text
BO_MCP/
├── core/
│   ├── auth/                  # Enterprise credential resolution (Keyring, Env, CLI, Auto-discovery)
│   │   ├── __init__.py
│   │   ├── cli.py             # Masked getpass setup wizard (configure, status, test, clear)
│   │   ├── models.py          # AuthCredentials with Pydantic SecretStr protection
│   │   └── providers.py       # ChainedCredentialProvider, Env, Keyring with auto-discovery
│   ├── session.py             # SessionManager & UserSession for multi-user/client isolation
│   ├── client.py              # BOEClient: HTTP keep-alive session, token lifecycle, error handling
│   ├── exceptions.py          # Custom domain exceptions (BOEAuthError, BOEProcessingError, etc.)
│   └── models.py              # Pydantic v2 schemas: BatchDiagnosticsReport, ClusterDiagnosis, etc.
├── wiki/                      # Self-contained LLM-Wiki (Karpathy + Google OKF specification)
│   ├── index.md               # Global OKF catalog & progressive disclosure entry point
│   ├── log.md                 # Chronological append-only operation log
│   ├── raw/                   # Immutable primary sources & original design RFCs
│   ├── architecture/          # System design, Enterprise Auth, Sessions & Diagnostics specs
│   ├── sap_bo/                # SAP BO 4.3 SP5 domain rules (CMS SQL, IDT vs CMC, Raylight)
│   ├── tools/                 # Complete MCP tool catalogs & Tier 1/Tier 2 safety matrices
│   └── troubleshooting/       # Error code triage runbooks (IES 10901, WIS 30553, ORA-01017)
├── services/
│   ├── __init__.py
│   ├── admin_service.py       # CMS Admin: generic SQL queries, users, groups, active sessions
│   ├── diagnostic_service.py  # Intelligent Diagnostics: error clustering, multi-cause ranking, RCA
│   ├── infostore_service.py   # InfoStore: recursive folder traversal, categories, Webi lists
│   ├── schedule_service.py    # Schedules: recurring jobs, instance history, failure diagnostics
│   ├── universe_service.py    # Universes: UNX/UNV, semantic hierarchy (/sl/v1), lineage
│   └── webi_service.py        # Web Intelligence: prompts, LOVs, refresh, tables, formulas, SQL
├── server.py                  # FastMCP server exposing 48 typed MCP tools + Auth CLI subcommands
├── sdk_parser_new.py          # Unified Facade ensuring 100% backward compatibility
├── .agents/
│   └── mcp_config.json        # Workspace configuration for Antigravity IDE
├── .env                       # Local environment secrets (excluded from git)
├── .env.example               # Clean configuration template
└── README.md
```

### System Flow Diagram

```text
+-------------------------------------------------------------+
|                     AI Agent Surface                        |
|   (Antigravity IDE / Antigravity CLI "agy" / Claude Desktop)|
+------------------------------+------------------------------+
                               |
                   JSON-RPC over STDIO
                               |
                               v
+-------------------------------------------------------------+
|                    FastMCP Server (server.py)               |
|  - Exposes 48 MCP Tools with docstrings & typed schemas     |
|  - Subcommands: configure, status, test, clear              |
+------------------------------+------------------------------+
                               |
              SessionManager (core/session.py)
              Resolves credentials via ChainedCredentialProvider
              (Priority 1: .env -> Priority 2: OS Keyring)
                               |
                               v
+-------------------------------------------------------------+
|               Domain Services Layer (services/)             |
|  ├── DiagnosticService  (Batch RCA, Error Clustering, Models)|
|  ├── WebiService        (Prompts, Refresh, Blocks, SQL)     |
|  ├── UniverseService    (Semantic Tree, Lineage, UNX/UNV)   |
|  ├── ScheduleService    (Instances, Diagnostics, Jobs)      |
|  ├── AdminService       (CMS SQL Query, Users, Groups)      |
|  └── InfostoreService   (Folders, Categories)               |
+------------------------------+------------------------------+
                               |
                   BOEClient (core/client.py)
                   - Isolated per UserSession
                   - requests.Session() keep-alive
                   - X-SAP-LogonToken lifecycle
                   - Configurable timeouts (default 120s)
                               |
                               v
+-------------------------------------------------------------+
|            SAP BusinessObjects Enterprise (biprws)          |
|  ├── /biprws/logon/long       (Authentication)              |
|  ├── /biprws/raylight/v1      (Web Intelligence API)        |
|  ├── /biprws/sl/v1            (Semantic Layer API)          |
|  ├── /biprws/infostore        (InfoStore Hierarchy API)     |
|  └── /biprws/v1/cmsquery      (Central Management Server)   |
+-------------------------------------------------------------+
```

---

## Available MCP Tools Reference (56 Tools)


### 1. Authentication (2 Tools)
| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `login` | `username?`, `password?` | Authenticates against SAP BO, acquiring the `X-SAP-LogonToken`. Falls back to `.env` if omitted. |
| `logout` | _none_ | Closes the active session on the BI platform and invalidates the session token. |

### 2. Universes & Semantic Layer (5 Tools)
| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `get_universes` | _none_ | Lists all published UNX and UNV universes (ID, name, folder ID). |
| `get_universe_details` | `universe_id` | Retrieves universe type (`unx`/`unv`), name, and CUID. |
| `get_universe_structure` | `universe_id` | Traverses the full business layer tree (classes, dimensions, measures, attributes, hierarchies). |
| `get_universe_related_reports` | `universe_id` | Queries the CMS to find all Webi reports referencing the universe (`SI_SL_DOCUMENTS` / `SI_WEBI`). |
| `get_universe_connection_id` | `universe_id` | Retrieves the Data Connection ID associated with the universe. |

### 3. Web Intelligence Documents & Lifecycle (6 Tools)
| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `get_documents` | `page=1`, `pagesize=50` | Retrieves a paginated list of Webi documents from the repository. |
| `get_doc_details` | `webi_doc_id` | Retrieves report metadata: name, folder path, CUID, scheduled status, and state. |
| `get_doc_properties` | `webi_doc_id` | Retrieves document configuration properties (refreshOnOpen, autoRefresh, etc.). |
| `save_webi_doc` | `webi_doc_id`, `webi_doc_name` | Saves/overwrites a Webi document while preserving user comments. |
| `delete_webi_doc` | `webi_doc_id` | Permanently deletes a Webi document from the CMS repository. |
| `export_webi_doc` | `webi_doc_id`, `export_format='pdf'`, `report_id?`, `output_path?`, `refresh=False` | Exports a Webi document or report tab to PDF, Excel (.xlsx), or CSV with optional in-session refresh. |

### 4. Webi Prompts, Parameters & Refresh (3 Tools)
| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `get_doc_parameters` | `webi_doc_id` | Lists all prompt parameters (ID, prompt question, technical name, data type, optional/mandatory flag). |
| `get_parameter_lov` | `webi_doc_id`, `parameter_id` | Retrieves the List of Values (LOV) allowed for a constrained prompt parameter. |
| `refresh_webi_doc` | `webi_doc_id`, `parameters?` | Injects prompt answers and triggers report calculation in the active session. |

### 5. Webi Tabs, Blocks & Tabular Data (5 Tools)
| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `get_reports` | `webi_doc_id` | Lists all sheets/tabs in a Webi document (returns report IDs and tab names). |
| `get_report_elements` | `webi_doc_id`, `report_id` | Lists all visual elements (tables, charts, sections) inside a report tab. |
| `get_report_element_data` | `webi_doc_id`, `report_id`, `element_id`, `max_rows=1000` | Extracts structured tabular data rows from a table block up to `max_rows`. |
| `get_variables` | `webi_doc_id` | Retrieves all calculated variables and custom formulas defined in a document. |
| `get_comments` | `webi_doc_id` | Retrieves collaborative user comments and cell annotations. |

### 6. Data Providers, SQL & Change Data Source (8 Tools)
| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `get_dp` | `webi_doc_id` | Lists all Data Provider identifiers (e.g. `DP0`, `DP1`) in a document. |
| `get_dp_details` | `webi_doc_id`, `dp_id` | Retrieves data source name, ID, type, and update status for a Data Provider. |
| `get_dp_sql` | `webi_doc_id`, `dp_id` | **Extracts the raw SQL query** statement generated by the Semantic Layer. |
| `get_dp_specification` | `webi_doc_id`, `dp_id` | Retrieves query specification tree (result objects, query filters, sort rules) via XML specification. |
| `refresh_dp` | `webi_doc_id`, `dp_id` | Refreshes a single Data Provider without recalculating the rest of the report. |
| `purge_dp` | `webi_doc_id`, `dp_id` | Purges cached data rows from a Data Provider to reduce storage size. |
| `get_dp_mapping_proposal` | `webi_doc_id`, `dp_id`, `target_datasource_id`, `strategies?`, `resolve_names?` | **Evaluates Change Data Source mapping strategies** (UNV to UNX or repointing), returning matching statuses (`Ok`, `Ambiguous`, `NotFound`), match rates, and human-readable object names. |
| `change_dp_datasource` | `webi_doc_id`, `dp_id`, `target_datasource_id`, `strategies?`, `custom_mappings?`, `save?` | **Executes Change Data Source** on a Data Provider, applies strategy matches and custom overrides, submits changes to Raylight, and commits to the repository. |

#### Change Data Source & Mapping Strategies Evaluation

When migrating reports from UNV to UNX or repointing between universes, the SAP Raylight REST engine evaluates objects using one or more mapping strategies from left to right:

| Strategy | Matching Mechanism | Precision & Safety | Best Used For |
| :--- | :--- | :--- | :--- |
| **`SameID`** | Matches exact internal object IDs (`OBJ_...`). | **100% Deterministic** (Zero risk). | **UNV -> UNX migrations** where the UNX was converted using Information Design Tool (IDT), which preserves original IDs. |
| **`SamePath`** | Matches full qualified folder tree path (`[Class]/[Subclass]/[Object]`). | **Very High (98%)** (Safe). | Distinguishes homonyms safely (e.g. `[Customer]/[Country]` vs `[Supplier]/[Country]`) even if IDs were regenerated. |
| **`SameName`** | Matches exact object display names regardless of folder hierarchy. | **High (85-90%)**. | Universes where classes or folders were reorganized or flattened, but business object names were kept identical. |
| **`SameTechnicalName`** | Matches underlying database column or technical field name. | **High (85%)**. | Scenarios where business names were translated or rebranded, but database column names remain unchanged. |
| **`CloseName`** | Fuzzy string distance (Levenshtein) matching. | **Medium / Caution**. | Minor spelling adjustments or plurals. May produce false positives; recommended only with manual review. |

> [!TIP]
> **Recommended Strategy Chain**: `SameID,SamePath,SameName` (The **Gold Standard** default).
> It guarantees 100% precision for IDT-converted universes, resolves structural hierarchy matches next, and gracefully falls back to display name matching without risking the false positives associated with uncontrolled fuzzy matching. Custom mapping overrides (`custom_mappings=[{"source_id": "...", "target_id": "..."}]`) can be supplied for any unresolved edge cases.

### 7. Central Management Server (CMS) Admin & Security (8 Tools)
| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `cms_query` | `query`, `page=1`, `pagesize=1000` | **Executes arbitrary CMS SQL queries** against `CI_INFOOBJECTS`, `CI_APPOBJECTS`, `CI_SYSTEMOBJECTS`. |
| `get_users` | `page=1`, `pagesize=100` | Lists user accounts (ID, username, email, disabled status, last logon). |
| `get_user_details` | `user_id` | Retrieves full profile properties of a specific user ID. |
| `set_user_status` | `user_id`, `disabled: bool` | Enables (`disabled=False`) or disables (`disabled=True`) a user account. |
| `get_user_groups` | `page=1`, `pagesize=100` | Retrieves all User Groups along with member counts. |
| `get_group_users` | `group_id` | Lists all users that are members of a specific User Group. |
| `get_active_sessions` | _none_ | Monitors active connections and user sessions open on the CMS. |
| `terminate_session` | `session_id` | Forcibly terminates an active connection session by connection ID. |

### 8. Schedules & Instance Diagnostics (4 Tools)
| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `get_doc_schedules` | `webi_doc_id` | Lists scheduled execution rules defined for a Webi document. |
| `get_doc_instances` | `webi_doc_id`, `max_instances=50` | Retrieves historical run instances (*Success*, *Failed*, *Running*) with timestamps. |
| `get_instance_details` | `instance_id` | Retrieves diagnostic information for an instance run, including failure error messages. |
| `delete_instance` | `instance_id` | Deletes a historical report execution instance from the CMS repository. |

### 9. InfoStore, Folders & Categories (6 Tools)
| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `get_folders` | `folder_id` | Recursively traverses subfolder IDs starting from a parent folder. |
| `get_folder_details` | `folder_id` | Retrieves metadata of a repository folder (name, CUID, parent ID, description). |
| `create_folder` | `name`, `parent_folder_id`, `description?` | Creates a new folder in the InfoStore repository under a parent folder. |
| `delete_folder` | `folder_id` | Permanently deletes a folder from the InfoStore repository. |
| `get_webi_docs` | `folder_id` | Lists all Webi document IDs located directly inside a repository folder. |
| `get_categories` | _none_ | Lists all Corporate Categories defined in the BI platform repository. |

### 10. Intelligent Diagnostics & Batch Health Monitoring (1 Tool)
| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `diagnose_batch_failures` | `hours_back=12`, `kind='All'`, `folder_id?`, `max_instances=100` | **Scans, deduplicates, and diagnoses batch failures** for Webi reports and Publications (`SI_SCHEDULE_STATUS = 3`). Clusters failures by error signature and produces a structured Pydantic v2 RCA report with up to 3 ranked probable causes and actionable remediation steps. |

#### Automated Root Cause Analysis (RCA) & Error Clustering

The `diagnose_batch_failures` tool automates nocturnal batch monitoring and incident triage by querying the CMS repository (`CI_INFOOBJECTS`) via `POST /biprws/v1/cmsquery` for instances with `SI_SCHEDULE_STATUS = 3` (Failed).

1. **Error Normalization**: Recursively extracts text from nested CMS error structures (`SI_STATUSINFO`, `SI_SUBST_STRINGS`, `SI_RESOURCEID`), strips volatile runtime noise (timestamps, thread PIDs, hex addresses, IP addresses), and isolates standard SAP BO and database error codes (`WIS`, `ORA`, `CRS`, `FBE`, socket timeouts).
2. **Signature Clustering & Deduplication**: Groups identical failures into clusters using deterministic SHA-256 fingerprinting. This prevents LLM context exhaustion when diagnosing hundreds of batch failures.
3. **Smart Context Enrichment**: For clusters linked to prompt or calculation errors (`WIS 30270`, `WIS 30271`), automatically queries `/biprws/raylight/v1/documents/{id}/parameters` to identify unmapped or missing mandatory prompt parameters.
4. **Multi-Cause Ranking & Actionable Remediation**: Assigns up to 3 ranked potential causes per cluster with confidence scores (`probability_score`) and concrete administrator remediation actions.
5. **Pydantic v2 Structured Output**: Returns a strictly validated `BatchDiagnosticsReport` model for programmatic consumption.

| Failure Category | Error Codes / Patterns | Typical Root Cause | Recommended Administrator Action |
| :--- | :--- | :--- | :--- |
| **`DB_LOCK_CONCURRENCY`** | `ORA-00060`, deadlock, lock request time out | Heavy transactional lock contention on data warehouse staging tables | Review DBA concurrent sessions, introduce job staggering (15-30 min intervals) |
| **`AUTH_CREDENTIALS`** | `ORA-01017`, invalid username/password, logon denied | Expired DB technical service account or rotated password | Test relational connection (.cns/.cnx) in Information Design Tool (IDT) and update credentials |
| **`NETWORK_TIMEOUT`** | SocketTimeoutException, Connection refused, timed out | Database listener or network firewall dropped keep-alive | Verify database server reachability, check listener port and connection pool timeouts |
| **`MISSING_PROMPTS`** | `WIS 30270`, `WIS 30271`, missing mandatory parameter | Scheduled instance triggered without required parameter values | Inspect report prompt rules in CMS and supply missing default prompt answers |
| **`CACHE_CORRUPTED`** | `WIS 30553`, processDPCommandsEx | Corrupted microcube cache in Web Intelligence Processing Server | Purge data provider cache via `purge_dp` or resave document definition |
| **`BURSTING_RECIPIENT`** | `FBE60502`, `CRS 30000`, Publication error | Dynamic recipient source document empty or unmapped email attribute | Verify recipient query results and publication delivery destination mapping |
| **`SERVER_RESOURCE_OOM`** | OutOfMemoryError, Java heap space, GC overhead | Adaptive Processing Server (APS) or Webi Processing Server memory exhaustion | Increase JVM max heap allocation (`-Xmx`) in CMC server properties and restart service |

> [!NOTE]
> In SAP BusinessObjects 4.x, relational connection testing (`.cns` / `.cnx` for UNX) is supported exclusively through the **Information Design Tool (IDT)** (or Universe Design Tool for legacy `.unv`). The Central Management Console (CMC) does not provide a relational connection testing function.

### 11. Local SAP BO Server Log Inspection — Admin-Only (3 Tools)
When `bo-mcp` runs co-located on the SAP BusinessObjects host, `LogService` streams `.glf` (pipe-delimited Generic Log Format), `.log`, and `.trc` files in reverse order (64 KB chunks from EOF) without loading large trace files into RAM. Protected by strict path-traversal sandboxing (`SAP_BO_LOG_DIR`) and SAP BO `Administrators` RBAC.

| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `list_bo_logs` | `server_type?`, `hours_back=24`, `max_files=100` | **[Admin-Only]** Lists recent SAP BO server log files (`.glf`, `.log`, `.trc`) grouped by component (`WebiProcessingServer`, `AdaptiveJobServer`, `CMS`, `WACS`). |
| `search_bo_logs` | `pattern`, `server_type?`, `hours_back=12`, `severity?`, `max_matches=50` | **[Admin-Only]** Streams and searches recent `.glf`/`.log` files for error codes (`IES 10901`, `WIS 30553`, `ORA-01017`), CUIDs, or regex patterns. |
| `get_bo_log_context` | `file_name`, `line_number`, `context_lines=20` | **[Admin-Only]** Retrieves surrounding lines before and after a specific 1-based line number to inspect full stack traces. |

### 12. Auditing Database ODBC Introspection — Admin-Only (4 Tools)
`AuditService` connects directly to the SAP BusinessObjects Auditing Database (`ADS_*` schema) via the host's native ODBC configuration (`pyodbc`, `readonly=True`), enforcing a strict `SELECT`/`WITH`-only SQL validator and RDBMS-agnostic row capping (`cursor.fetchmany`).

| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `get_audit_failed_events` | `hours_back=24`, `event_type_id?`, `max_rows=100` | **[Admin-Only]** Queries `ADS_EVENT` for failed platform events (`Status_ID <> 0` excluding successful statuses, decoded via `ADS_STATUS_STR`, with the error text from `ADS_EVENT_DETAIL`). |
| `get_audit_heavy_reports` | `days_back=7`, `top_n=20` | **[Admin-Only]** Identifies the slowest and heaviest reports in `ADS_EVENT` ranked by maximum and average `Duration_ms`. |
| `get_audit_user_activity` | `username?`, `hours_back=24`, `max_rows=100` | **[Admin-Only]** Retrieves recent user logons, document views, refreshes, and exports from `ADS_EVENT`. |
| `query_audit_db` | `sql_query`, `max_rows=200` | **[Admin-Only]** Executes a custom, strictly read-only `SELECT` query against `ADS_*` tables (multi-statement `;` and DML/DDL keywords are blocked). |

### 13. MCP Server Self-Diagnostics & Remote Troubleshooting (1 Tool)
| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `get_mcp_server_diagnostics` | `include_recent_logs=True`, `max_log_lines=50` | **Probes all 4 server subsystems** (OS/Runtime & RBAC session state, `biprws` HTTP reachability & latency, `SAP_BO_LOG_DIR` permissions, `pyodbc` drivers & live Auditing DB ping) plus sanitized internal `bo-mcp` logs from the in-memory ring buffer so an AI agent can diagnose remote server issues directly over MCP. |

---

## Environment Variables

| Variable | Required? | Default | Description | Example |
| :--- | :---: | :---: | :--- | :--- |
| `SAP_BO_REST_API_URL` | **Yes** | `None` | URL to SAP BI Platform REST Web Services (`biprws`) | `http://localhost:6405/biprws` |
| `SAP_BO_USERNAME` | Optional | `None` | Default username for local `stdio` mode | `Administrator` |
| `SAP_BO_PASSWORD` | Optional | `None` | Default password for local `stdio` mode | `SecretP@ssw0rd` |
| `SAP_BO_ADMIN_GROUPS` | Optional | `Administrators` | Comma-separated SAP BO UserGroups authorized for Admin-only tools | `Administrators,BO_Ops` |
| `MCP_TRANSPORT` | Optional | `stdio` | Transport mode (`stdio`, `streamable-http`, `sse`) | `streamable-http` |
| `MCP_HOST` | Optional | `0.0.0.0` | Bind address when running in `streamable-http` or `sse` mode | `0.0.0.0` |
| `MCP_PORT` | Optional | `8000` | Bind port when running in `streamable-http` or `sse` mode | `8000` |
| `MCP_SSL_CERTFILE` | Optional | `None` | PEM certificate (chain) file; with `MCP_SSL_KEYFILE` enables **HTTPS** | `/etc/bo-mcp/tls/server.pem` |
| `MCP_SSL_KEYFILE` | Optional | `None` | PEM private key file for HTTPS | `/etc/bo-mcp/tls/server.key` |
| `MCP_SSL_KEYFILE_PASSWORD` | Optional | `None` | Passphrase of an encrypted private key | `KeyPass` |
| `SAP_BO_CA_FILE` | Optional | `None` | *(Client bridge)* CA bundle / self-signed cert to trust for `https://` URLs | `/path/to/ca.pem` |
| `SAP_BO_TLS_INSECURE` | Optional | `false` | *(Client bridge)* Disable TLS verification, **development only** | `true` |
| `SAP_BO_LOG_DIR` | Optional | Auto-detected | Path to local SAP BusinessObjects `logging/` directory | `/opt/bobj/sap_bobj/logging` |
| `SAP_BO_AUDIT_DSN` | Optional | `None` | System ODBC DSN name for the SAP BO Auditing Database | `BI4_Audit_DSN_1651343769` |
| `SAP_BO_AUDIT_USER` | Optional | `None` | Auditing Database username | `dba` |
| `SAP_BO_AUDIT_PASSWORD` | Optional | `None` | Auditing Database password (masked via `SecretStr`) | `AuditSecret` |
| `SAP_BO_AUDIT_TIMEOUT` | Optional | `20` | Query timeout in seconds for Auditing DB ODBC connections | `20` |
| `MCP_SERVER_LOG_FILE` | Optional | `None` | Optional file path for rotating internal `bo-mcp` server logs | `/var/log/bo-mcp/bo-mcp.log` |

---

## Co-Located Remote Deployment (Linux & Windows Server)

You can use `bo-mcp` **both locally via `STDIO`** (on your laptop) and **remotely via `Streamable HTTP` or `SSE`** (installed directly on the SAP BusinessObjects server).

### 1. Starting the Remote Server Manually
On the SAP BusinessObjects machine (Linux or Windows):
```bash
# Streamable HTTP (Recommended for remote MCP clients, exposes http://<bo-host>:8000/mcp)
uv run python server.py --transport streamable-http --host 0.0.0.0 --port 8000

# Or Server-Sent Events (exposes http://<bo-host>:8000/sse)
uv run python server.py --transport sse --host 0.0.0.0 --port 8000
```

#### Optional: HTTPS (TLS)
HTTP and HTTPS are both supported; the scheme is chosen purely by configuration. Without certificate options the server serves plain HTTP (a warning is logged when binding to a non-loopback address, because credentials travel in `x-sap-*` headers). To enable HTTPS pass a certificate and key (or set `MCP_SSL_CERTFILE` / `MCP_SSL_KEYFILE` in `.env`, which also works for the systemd/Windows service):
```bash
uv run python server.py --transport streamable-http --host 0.0.0.0 --port 8443 \
    --ssl-certfile /etc/bo-mcp/tls/server.pem --ssl-keyfile /etc/bo-mcp/tls/server.key
```
The server refuses to start if only one of the two files is given or a file is missing (it never silently falls back to HTTP).

- **Production:** use a certificate issued by your corporate CA (or terminate TLS on a reverse proxy such as nginx/IIS in front of `bo-mcp`).
- **Development / test:** generate a self-signed certificate (cross-platform, no `openssl` needed):
  ```bash
  uv run python deploy/generate_dev_cert.py --host <bo-host-or-ip>   # -> certs/dev-cert.pem, certs/dev-key.pem
  ```
  Copy **only** `dev-cert.pem` to your workstation and trust it in the bridge with `--ca-file` (see below). `certs/`, `*.pem` and `*.key` are git-ignored.

### 2. Installing as a Native System Service
- **Linux (`systemd`):** Copy [`deploy/bo-mcp.service`](deploy/bo-mcp.service) to `/etc/systemd/system/bo-mcp.service` (pre-configured to run as the `bobj` OS user and load `ODBCINI` and `LD_LIBRARY_PATH` from `/opt/bobj/sap_bobj/enterprise_xi40/odbc.ini`), then run:
  ```bash
  sudo systemctl daemon-reload
  sudo systemctl enable --now bo-mcp.service
  ```
- **Windows Server (`Windows Service`):** Run [`deploy/windows_service_setup.ps1`](deploy/windows_service_setup.ps1) in an elevated PowerShell prompt to register `SAPBusinessObjectsMCP` via `NSSM` or `sc.exe`.

#### Auditing Database prerequisites (host)
The audit tools need `pyodbc` (optional extra `audit`, installed by `deploy/setup_*`) plus the unixODBC runtime and the ODBC driver of the auditing database on the host:
```bash
uv sync --extra audit                      # installs pyodbc (use this instead of plain `uv sync`)
sudo dnf install unixODBC                  # RHEL/Oracle Linux; Debian/Ubuntu: sudo apt install unixodbc
export ODBCINI=/opt/bobj/sap_bobj/enterprise_xi40/odbc.ini   # the systemd unit already sets it
grep -n "^\[" "$ODBCINI"                   # SAP_BO_AUDIT_DSN must match one of these DSN names exactly
uv run python server.py doctor             # section "auditing_db_odbc" shows driver/DSN/connection status
```

### 3. Connecting Your Local MCP Client to the Remote Server

You can connect your desktop MCP host (Google Antigravity IDE, Claude Desktop, Cursor) to the remote SAP BO server using two approaches:

#### Option A: Local Keyring Bridge (Zero-Password / Automatic Keyring Integration)
The recommended approach for macOS and Windows desktops. The lightweight bridge [`deploy/client_bridge.py`](deploy/client_bridge.py) runs locally on your Mac/Windows PC, resolves your credentials from your **macOS Keychain** or **Windows Credential Manager** (`python deploy/client_bridge.py configure`), and connects to the remote server over Streamable HTTP, authenticating your session automatically:

```json
{
  "mcpServers": {
    "sap-business-objects": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/BO_MCP",
        "run", "python", "deploy/client_bridge.py",
        "--remote-url", "http://your-bo-server:8000"
      ]
    }
  }
}
```
*Zero passwords in chat, zero plaintext secrets on the remote server.*

For HTTPS use an `https://` URL. If the server certificate is signed by a private CA or is self-signed, trust it explicitly:
```json
"--remote-url", "https://your-bo-server:8443",
"--ca-file", "/path/to/ca-or-dev-cert.pem"
```
`--insecure` (or `SAP_BO_TLS_INSECURE=true`) disables certificate verification and is meant for development only. The bridge logs a warning when your password is about to be sent over plain `http://` to a non-loopback host.

#### Option B: Direct HTTP Endpoint
Point your MCP client directly to the remote URL:
```json
{
  "mcpServers": {
    "sap-business-objects": {
      "url": "http://your-bo-server:8000/mcp"
    }
  }
}
```
Once connected, either invoke `login(username="...", password="...")` in chat or configure fallback credentials in the remote server's `.env`. All tools are executed remotely on the SAP BO host.

### 4. Remote Troubleshooting (`get_mcp_server_diagnostics` & `python server.py doctor`)
If any subsystem fails while `bo-mcp` is running remotely on the SAP BO server:
1. **Directly from Chat (No SSH Required):** Ask the AI agent: *"Run `get_mcp_server_diagnostics` to check why the remote server is failing."* The agent receives a secret-masked JSON report covering OS/user context, `biprws` reachability, `SAP_BO_LOG_DIR` permissions, `pyodbc` installed drivers / `ODBCINI`, and the last 50 lines of `bo-mcp`'s internal error ring buffer.
2. **From the Server Terminal (CLI Doctor):** Run `uv run python server.py doctor` on the SAP BO host to print the complete 4-subsystem JSON diagnostic probe immediately.

---

## Client Integration Guide

### 1. Google Antigravity IDE

#### Workspace Configuration
Create a `.agents/mcp_config.json` file in your workspace (see [`mcp_config.example.json`](file:///mcp_config.example.json)). When you open this folder in Antigravity IDE, all 48 tools are registered automatically:

```json
{
  "mcpServers": {
    "sap-business-objects": {
      "command": "uv",
      "args": ["run", "python", "server.py"],
      "env": {}
    }
  }
}
```

#### Natural Language Prompts in Sidebar Chat (Agent Mode)
- *"Log into SAP BusinessObjects and perform intelligent diagnostics on batch executions that failed in the last 12 hours."*
- *"Execute a CMS query to list all Webi report instances that failed scheduling today."*
- *"Extract the raw SQL query generated by data provider DP3 of Webi report 6096."*
- *"Inspect prompt parameters for report 12345, answer with year=2026, and trigger a document refresh."*
- *"List all user accounts in the Administrators group and inspect active CMS sessions."*
- *"Traverse the corporate repository hierarchy starting from Public Folders (ID 23)."*


---

### 2. Antigravity CLI (`agy`)

Add the server to `~/.gemini/config/mcp_config.json`:

```json
{
  "mcpServers": {
    "sap-business-objects": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/BO_MCP",
        "run",
        "python",
        "server.py"
      ]
    }
  }
}
```

Run `agy` and prompt directly:

```bash
agy
> Login to SAP BusinessObjects and list all active CMS sessions.
```

---

### 3. FastMCP Development Inspector (Web UI)

Test tools via an interactive browser form:

```bash
uv run fastmcp dev server.py
```

---

### 4. Claude Desktop & Other MCP Hosts

For Anthropic Claude Desktop, add the configuration to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows).

With credentials stored securely in your OS Keyring, **no passwords or usernames are needed in the config**:

```json
{
  "mcpServers": {
    "sap-business-objects": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/BO_MCP",
        "run",
        "python",
        "server.py"
      ],
      "env": {
        "SAP_BO_REST_API_URL": "http://your-bo-host:8080/biprws"
      }
    }
  }
}
```

---

## Agent Skill: `sap-business-objects`

The repository includes a production-grade operational skill located at [`.agents/skills/sap-business-objects`](file:///.agents/skills/sap-business-objects), designed for **Google Antigravity**, **Gemini CLI (`agy`)**, and compatible autonomous AI agents.

### Core Capabilities:
- **Autonomous Intent Routing:** Matches user prompts to the exact MCP tools across 7 operational domains (universes, Webi documents, prompts, tabular data, exports, CMS administration, and batch failure RCA).
- **Safe-by-Default Action Tiers:** Enforces confirmation protocols for destructive actions (e.g., `delete_webi_doc`, `terminate_session`, `set_user_status`) while running safe queries autonomously.
- **Dedicated Operational Runbooks:**
  - [`semantic_and_webi.md`](file:///.agents/skills/sap-business-objects/references/semantic_and_webi.md): Step-by-step guidance for universes, SQL extraction, table block extraction, and in-session refreshed PDF/Excel/CSV exports.
  - [`cms_admin_and_security.md`](file:///.agents/skills/sap-business-objects/references/cms_admin_and_security.md): Virtual table querying (`CI_INFOOBJECTS`, `CI_SYSTEMOBJECTS`, `CI_APPOBJECTS`), session monitoring, and user/group administration.
  - [`batch_diagnostics_and_schedules.md`](file:///.agents/skills/sap-business-objects/references/batch_diagnostics_and_schedules.md): Root cause analysis (RCA) for nocturnal batch failures, error clustering, and strict IDT connection testing rules.
- **Repository Rules ([`project_rules.md`](file:///.agents/rules/project_rules.md)):** Defines architectural standards and enforces that SAP BusinessObjects relational connection testing is performed exclusively via the Information Design Tool (IDT), never the Central Management Console (CMC).

---

## Available Scripts & Commands

| Command | Purpose |
| :--- | :--- |
| `uv sync --dev` | Install all dependencies including testing and linting tools |
| `uv run python server.py configure` | Interactive setup wizard to securely store credentials in OS Keyring (masked `getpass`) |
| `uv run python server.py status` | Inspect currently active resolved credentials and target URL |
| `uv run python server.py test` | Verify stored credentials live against the SAP BO REST platform |
| `uv run python server.py clear` | Securely delete credentials from OS Keyring and local config metadata |
| `uv run python server.py doctor` | Run 4-subsystem self-diagnostic health probe (`biprws`, `SAP_BO_LOG_DIR`, `pyodbc` Auditing DB, runtime) |
| `uv run python server.py --transport streamable-http --host 0.0.0.0 --port 8000` | Start the MCP server in remote multi-tenant `Streamable HTTP` mode |
| `uv run pytest` | Run offline unit test suite with coverage report (130 tests) |
| `uv run ruff check .` | Run fast linting and style validation |
| `uv run fastmcp inspect server.py` | Inspect registered tools (verifies all 56 tools) |
| `uv run fastmcp dev server.py` | Launch interactive web inspector for live debugging |
| `uv run python server.py` | Run the MCP server in STDIO mode |


---

## Testing & Verification

The project includes an **offline unit test suite** powered by `pytest`, `pytest-mock`, and `pytest-cov`.

### Why Offline Testing?
Because SAP BusinessObjects Enterprise (BOE) requires a complex, proprietary on-premise installation and commercial licenses, tests are designed to execute **completely offline in < 1 second** without connecting to a live SAP server. They simulate:
- HTTP status codes (`200`, `401 Unauthorized`, `404 Not Found`, `500 Internal Server Error`).
- SAP BI platform specific error payloads (`WSR 00999`, invalid session tokens).
- REST content negotiation (JSON vs. XML `Accept: text/xml` headers for query specifications).
- Automatic and custom mapping strategies for changing Webi data sources.
- Integrity and docstring coverage for all 48 FastMCP tools.
- Intelligent diagnostics error signature clustering, multi-cause ranking, and Pydantic validation.


### Running Tests Locally
```bash
# Run all unit tests
uv run pytest

# Run with test coverage report
uv run pytest --cov=core --cov=services --cov=server --cov-report=term-missing

# Run code style & formatting checks
uv run ruff check .
uv run ruff format --check .
```

---

## Contributing Guidelines

Contributions are welcome! Whether you are fixing bugs, adding new SAP BO REST tools, or improving documentation, we appreciate your help.

For full contribution details, please read [CONTRIBUTING.md](CONTRIBUTING.md).

### Quick Contribution Workflow

1. **Fork & Clone**: Fork the repository on GitHub and clone your fork locally.
2. **Environment Setup**: Install development dependencies with `uv sync --dev`.
3. **Branching**: Create a focused feature branch off `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```
4. **Code Standards**:
   - Follow PEP 8 and project style using `uv run ruff check --fix .` and `uv run ruff format .`.
   - Maintain type annotations and descriptive docstrings for all `@mcp.tool()` functions.
   - Keep domain business logic inside `services/` and transport/session logic inside `core/client.py`.
5. **Testing**:
   - Add offline unit tests in `tests/` using `MockBOEClient`. **Do not write tests that require a live SAP BO server.**
   - Ensure all existing and new tests pass: `uv run pytest`.
6. **Submit a Pull Request**: Push your branch to GitHub and open a Pull Request targeting `main`. The automated GitHub Actions CI will validate your PR against Python 3.13.

---

## Troubleshooting

| Symptom / Error | Probable Cause | Recommended Resolution |
| :--- | :--- | :--- |
| `WSR 00999: Internal Server Error` | Corrupt Web Intelligence report structure or invalid REST payload syntax. | Verify document ID via `get_documents`, ensure correct query specification XML, and inspect CMS logs. |
| `401 Unauthorized / Invalid Token` | The `X-SAP-LogonToken` has expired or credentials are invalid. | Run the `login` tool to refresh the session token. |
| `404 Not Found` | The requested document ID, universe ID, or folder ID does not exist in the CMS. | Query the CMS via `cms_query` to confirm object existence and verify folder permissions. |
| `Connection refused / timeout` | Network firewall or routing blocking access to the SAP BO REST port (default `6405` / `8080`). | Verify `BO_BASE_URL` in `.env` and verify connectivity using `curl -v http://<host>:<port>/biprws/infostore`. |

---

## Security & Operational Best Practices

1. **Protect Sensitive Credentials**: Never commit `.env` files, logon tokens, or CMS credentials to source control. Use `.env.example` as a template.
2. **Least Privilege**: Configure dedicated SAP BO service accounts with permissions restricted to the target universes, folders, and reports required for your AI workflows.
3. **Session Hygiene**: Always log off inactive sessions using the `logout` tool or terminate orphaned sessions via `terminate_session`.
4. **Production Safeguards**: Exercise caution when using destructive tools like `delete_webi_doc`, `delete_folder`, `purge_dp`, or `set_user_status`.

---

## Author & License

- **Author**: Alessio Ballarin ([@alexraio](https://github.com/alexraio))
- **Version**: `0.2.0` (Modular Domain Architecture)
- **License**: [Apache License 2.0](LICENSE) - see the [LICENSE](LICENSE) file for complete terms and copyright notices.
