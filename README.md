# SAP BusinessObjects MCP Server (`bo-mcp`)

[![FastMCP](https://img.shields.io/badge/FastMCP-2.13.1-blue.svg)](https://github.com/jlowin/fastmcp)
[![MCP](https://img.shields.io/badge/MCP-1.22.0-green.svg)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Package Manager](https://img.shields.io/badge/uv-package%20manager-purple.svg)](https://astral.sh/uv)
[![SAP BO](https://img.shields.io/badge/SAP%20BusinessObjects-BI%204.x%20%2F%20202x-orange.svg)](https://www.sap.com)

A Model Context Protocol (**MCP**) server that exposes **SAP BusinessObjects BI Platform** administration and inspection capabilities to AI coding assistants and autonomous agents. Built using **FastMCP 2.0** and the **SAP BI Platform REST Web Services (`biprws`)**, this server enables AI agents (such as **Google Antigravity IDE**, **Antigravity CLI `agy`**, Claude Desktop, and Cursor) to authenticate, discover universes, inspect Web Intelligence (Webi) reports, navigate repository folder structures, analyze data providers, and perform document maintenance tasks directly from natural language prompts.

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
  - [Directory Structure](#directory-structure)
  - [System Flow Diagram](#system-flow-diagram)
  - [Component Breakdown](#component-breakdown)
  - [Authentication & Session Lifecycle](#authentication--session-lifecycle)
  - [SAP BusinessObjects REST API Surface](#sap-businessobjects-rest-api-surface)
- [Available MCP Tools Reference](#available-mcp-tools-reference)
  - [Tool Summary Table](#tool-summary-table)
  - [Detailed Tool Specifications](#detailed-tool-specifications)
- [Environment Variables](#environment-variables)
- [Client Integration Guide](#client-integration-guide)
  - [1. Google Antigravity IDE](#1-google-antigravity-ide)
  - [2. Antigravity CLI (`agy`)](#2-antigravity-cli-agy)
  - [3. FastMCP Development Inspector (Web UI)](#3-fastmcp-development-inspector-web-ui)
  - [4. Claude Desktop & Other MCP Hosts](#4-claude-desktop--other-mcp-hosts)
- [Available Scripts & Commands](#available-scripts--commands)
- [Testing & Verification](#testing--verification)
- [Troubleshooting](#troubleshooting)
- [Security & Operational Best Practices](#security--operational-best-practices)
- [Author & License](#author--license)

---

## Key Features

- **Automated Authentication**: Log on using user/password or trusted credentials, retrieve and store the `X-SAP-LogonToken` transparently across sessions.
- **Semantic Layer & Universe Discovery**: Retrieve UNX and UNV universes, query details (type, CUID, name), and map relationships.
- **Webi Document Intelligence**: Extract Webi document metadata, folder paths, CUIDs, refresh/schedule statuses, and document states.
- **Data Provider Inspection & Purging**: Enumerate all queries and data providers within Webi reports, retrieve data source details, and purge data to reduce storage and reset cache before distribution.
- **Repository Hierarchy Traversal**: Recursively traverse CMS folder trees from any root folder and locate all Webi documents contained within.
- **CMS Query Integration**: Execute high-performance Central Management Server (CMS) queries using the BI Platform InfoStore and Semantic Layer APIs.
- **Document Lifecycle Actions**: Save/overwrite Webi reports with comments preserved, or safely remove obsolete documents.
- **Multi-Client Ready**: Fully compatible with Antigravity IDE, Antigravity CLI (`agy`), Claude Desktop, Cursor, and any MCP client supporting the `stdio` transport.

---

## Tech Stack

| Layer | Component | Version / Description |
| :--- | :--- | :--- |
| **Runtime** | Python | `>= 3.13` |
| **Package Management** | Astral `uv` | Fast virtual environment & dependency management via `pyproject.toml` |
| **MCP Framework** | `fastmcp` | `2.13.1` (FastMCP 2.0 Generation 2) |
| **MCP Specification** | `mcp` | `1.22.0` (Standard Model Context Protocol) |
| **HTTP Engine** | `requests` | `2.32.5` persistent HTTP sessions with `requests.Session()` |
| **Data Validation** | `pydantic` | `2.12.5` |
| **Configuration** | `python-dotenv` | `1.2.1` for loading `.env` configuration |
| **Target Platform** | SAP BusinessObjects BI | BI 4.2 / 4.3 / 202x with REST Web Services (`biprws`) enabled |

---

## Prerequisites

Before setting up the MCP server, ensure you have the following installed and accessible:

1. **Python 3.13+**: Verified with Python 3.13.0+.
2. **`uv` Package Manager** (recommended) or standard `pip` + `python3 -m venv`.
   - Install `uv` on macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Or via Homebrew: `brew install uv`
3. **Network Access to SAP BusinessObjects**:
   - Access to your SAP BI Platform REST Web Services URL (typically `http://<host>:<port>/biprws`).
   - A valid SAP BusinessObjects user account (e.g. Enterprise, LDAP, or WinAD) with rights to query the CMS and access Web Intelligence documents.

---

## Getting Started

### 1. Clone or Open the Repository

Clone the repository to your local workstation:

```bash
git clone https://github.com/your-username/BO_MCP.git
cd BO_MCP
```

### 2. Environment Configuration

Copy the sample environment file to create your local `.env`:

```bash
cp .env.example .env
```

Open `.env` in your text editor and configure your SAP BusinessObjects server URL and credentials:

```env
# SAP BusinessObjects REST API Configuration
SAP_BO_REST_API_URL="http://ora-rhel-01.pf.box:8080/biprws"

# Authentication Credentials
SAP_BO_USERNAME="Administrator"
SAP_BO_PASSWORD="YourPasswordHere"
```

> [!IMPORTANT]
> The `.env` file is excluded from git via `.gitignore`. Never commit actual SAP credentials to source control.

### 3. Install Dependencies

Using `uv` (recommended):

```bash
# Creates the virtual environment and installs all dependencies from uv.lock
uv sync
```

Alternatively, using standard `pip`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Verify MCP Server Installation

Run FastMCP inspection to verify that all 13 tools are properly registered and discoverable:

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
  Tools:        13
  Prompts:      0
  Resources:    0
  Templates:    0

Environment
  FastMCP:      2.13.1
  MCP:          1.22.0
```

---

## Architecture & Deep Dive

### Directory Structure

```text
BO_MCP/
├── .agents/
│   └── mcp_config.json      # Workspace MCP configuration for Antigravity IDE
├── .env                     # Local environment secrets (excluded from git)
├── .env.example             # Clean configuration template
├── .gitignore               # Git ignore rules (.env, .venv, __pycache__, etc.)
├── .python-version          # Python runtime pin (3.13)
├── pyproject.toml           # Project metadata and dependencies specification
├── README.md                # Comprehensive documentation
├── requirements.txt         # Pinned requirements for standard pip workflows
├── sdk_parser_new.py        # Core Python client for SAP BO REST APIs (BOESDKParser)
├── server.py                # FastMCP server exposing tool definitions
├── uv.lock                  # Deterministic dependency lockfile
└── .venv/                   # Local virtual environment created by uv
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
|  - Exposes 13 MCP Tools (@mcp.tool())                       |
|  - Manages FastMCP lifecycle and tool parameters            |
|  - Injects environment variables from .env                  |
+------------------------------+------------------------------+
                               |
                      Python Method Calls
                               |
                               v
+-------------------------------------------------------------+
|                BOESDKParser (sdk_parser_new.py)             |
|  - requests.Session() with persistent cookies & headers     |
|  - Handles X-SAP-LogonToken header lifecycle                |
|  - Builds and formats REST queries & CMS SQL payloads       |
+------------------------------+------------------------------+
                               |
                       HTTP / HTTPS REST
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

### Component Breakdown

1. **`server.py`**:
   - The primary entry point for MCP clients.
   - Instantiates `FastMCP("SAP Business Objects")`.
   - Reads `SAP_BO_REST_API_URL`, `SAP_BO_USERNAME`, and `SAP_BO_PASSWORD` via `python-dotenv`.
   - Parses the target host, protocol, and port, then initializes `BOESDKParser`.
   - Registers all 13 tools via `@mcp.tool()` decorators with typed parameters, clear docstrings, and robust exception-to-string mappings.
   - Runs `mcp.run()` using standard input/output (STDIO) transport.

2. **`sdk_parser_new.py` (`BOESDKParser`)**:
   - The low-level API client interfacing directly with the SAP BI REST Web Services.
   - Maintains a single persistent `requests.Session()` instance for efficient HTTP keep-alive connections.
   - Automatically handles token extraction and injects the header `X-SAP-LogonToken: <token>` into all subsequent requests.
   - Implements recursive folder traversal, CMS InfoStore queries, and Web Intelligence manipulation.

### Authentication & Session Lifecycle

Authentication follows the SAP BusinessObjects REST API two-stage handshake:

1. **Logon Template Retrieval**:
   - `GET /biprws/logon/long` returns the server's authentication template (specifying authentication scheme, e.g. `secEnterprise`).
2. **Credential Transmission**:
   - `POST /biprws/logon/long` sends `userName` and `password`.
   - The SAP BO server validates credentials and issues a cryptographic `logonToken`.
3. **Session State**:
   - The token is attached to the default session headers as `X-SAP-LogonToken`.
   - Subsequent calls to Raylight, InfoStore, and CMS Query reuse this session.
4. **Logoff**:
   - `POST /biprws/v1/logoff` invalidates the server session and closes the HTTP session.

### SAP BusinessObjects REST API Surface

| Endpoint Sub-path | Service Name | Responsibility |
| :--- | :--- | :--- |
| `/biprws/logon/long` | BI Platform Logon | User & password token-based authentication |
| `/biprws/logon/trusted` | Trusted Authentication | Single sign-on using trusted principal certificates |
| `/biprws/v1/logoff` | BI Platform Session | Session termination and token invalidation |
| `/biprws/raylight/v1/universes` | Raylight Universes | Enumerate published universes and retrieve universe CUID/type |
| `/biprws/raylight/v1/documents` | Raylight Webi | Webi document metadata, status, save, and delete |
| `/biprws/raylight/v1/documents/{id}/dataproviders` | Raylight Data Providers | Query inspection, data source IDs, and data provider purge |
| `/biprws/infostore/{id}/children` | InfoStore Navigation | Hierarchical folder and document tree enumeration |
| `/biprws/v1/cmsquery` | CMS Query Service | Direct relational SQL-like queries against `CI_APPOBJECTS` and `CI_INFOOBJECTS` |

---

## Available MCP Tools Reference

### Tool Summary Table

| Tool Name | Parameters | Returns | Destructive? | Description |
| :--- | :--- | :--- | :---: | :--- |
| `login` | `username?`, `password?` | `str` | No | Authenticate with SAP BO and set session token |
| `logout` | _none_ | `str` | No | Terminate session and close HTTP connection |
| `get_universes` | _none_ | `List[Dict]` | No | List all available universes with ID, name, folder ID |
| `get_universe_details` | `universe_id` | `Dict` | No | Retrieve universe type (`unx`/`unv`), name, and CUID |
| `get_universe_related_reports` | `universe_id` | `Dict` | No | Find all Webi reports referencing a specific universe |
| `get_folders` | `folder_id` | `List[str]` | No | Recursively list all folder IDs under a root folder |
| `get_webi_docs` | `folder_id` | `List[str]` | No | List all Webi document IDs in a specified folder |
| `get_doc_details` | `webi_doc_id` | `Dict` | No | Retrieve Webi report name, folder path, CUID, and state |
| `save_webi_doc` | `webi_doc_id`, `webi_doc_name` | `str` | **Yes** | Save/overwrite Webi document while preserving comments |
| `delete_webi_doc` | `webi_doc_id` | `str` | **Yes** | Permanently delete a Webi document from the CMS |
| `get_dp` | `webi_doc_id` | `List[str]` | No | List all Data Provider IDs in a Webi document |
| `get_dp_details` | `webi_doc_id`, `dp_id` | `Dict` | No | Get data source name, ID, and type for a data provider |
| `purge_dp` | `webi_doc_id`, `dp_id` | `str` | **Yes** | Purge cached data from a specific data provider |

---

### Detailed Tool Specifications

#### 1. `login`
- **Description**: Authenticates against the SAP BusinessObjects REST API. Must be called before running queries if the session is not yet established. If `username` or `password` are omitted, falls back to `SAP_BO_USERNAME` and `SAP_BO_PASSWORD` defined in `.env`.
- **Signature**: `login(username: str = None, password: str = None) -> str`
- **Example Response**:
  ```text
  "Login successful"
  ```

#### 2. `logout`
- **Description**: Closes the active session on the BI platform and invalidates the session token.
- **Signature**: `logout() -> str`
- **Example Response**:
  ```text
  "Logout successful"
  ```

#### 3. `get_universes`
- **Description**: Retrieves all universes published to the BI platform.
- **Signature**: `get_universes() -> List[Dict[str, str]]`
- **Example Response**:
  ```json
  [
    {
      "id": "582910",
      "name": "eFashion",
      "folderId": "6512"
    },
    {
      "id": "691420",
      "name": "Financials UNX",
      "folderId": "8901"
    }
  ]
  ```

#### 4. `get_universe_details`
- **Description**: Returns detailed metadata for a specific universe ID, including the universe engine type (`unx` for Information Design Tool or `unv` for Universe Design Tool).
- **Signature**: `get_universe_details(universe_id: str) -> Dict[str, str]`
- **Example Response**:
  ```json
  {
    "u_type": "unx",
    "u_name": "Financials UNX",
    "u_cuid": "AQb4Y0g7b6pEvM...kY"
  }
  ```

#### 5. `get_universe_related_reports`
- **Description**: Queries the CMS repository (`CI_APPOBJECTS`) to discover all Webi reports built upon the specified universe. Automatically handles schema differences between UNX (`SI_SL_DOCUMENTS`) and UNV (`SI_WEBI`).
- **Signature**: `get_universe_related_reports(universe_id: str) -> Dict[str, Any]`
- **Example Response**:
  ```json
  {
    "universe_id": "691420",
    "universe_name": "Financials UNX",
    "reports": ["120934", "120935", "121400"]
  }
  ```

#### 6. `get_folders`
- **Description**: Recursively traverses the CMS InfoStore hierarchy starting from `folder_id` and returns a flat list of all descendant folder IDs.
- **Signature**: `get_folders(folder_id: str) -> List[str]`
- **Example Response**:
  ```json
  ["1001", "1002", "1045", "1099"]
  ```

#### 7. `get_webi_docs`
- **Description**: Retrieves all Web Intelligence document IDs situated directly inside the specified folder.
- **Signature**: `get_webi_docs(folder_id: str) -> List[str]`
- **Example Response**:
  ```json
  ["239401", "239402", "240119"]
  ```

#### 8. `get_doc_details`
- **Description**: Returns detailed runtime and storage attributes of a Webi report.
- **Signature**: `get_doc_details(webi_doc_id: str) -> Optional[Dict[str, Any]]`
- **Example Response**:
  ```json
  {
    "webi_doc_name": "Monthly Sales Summary",
    "webi_doc_path": "Public Folders/Sales/EMEA",
    "webi_doc_cuid": "AX10b2k5m9pL...aZ",
    "webi_doc_scheduled": false,
    "webi_doc_state": "Unused"
  }
  ```

#### 9. `save_webi_doc`
- **Description**: Saves or overwrites a Webi document with a new or existing name while ensuring all user comments and annotations are preserved (`withComments=true`).
- **Signature**: `save_webi_doc(webi_doc_id: str, webi_doc_name: str) -> str`
- **Example Response**:
  ```text
  "Successfully saved document 239401 as Monthly Sales Summary"
  ```

#### 10. `delete_webi_doc`
- **Description**: Permanently deletes the specified Webi document from the repository.
- **Signature**: `delete_webi_doc(webi_doc_id: str) -> str`
- **Example Response**:
  ```text
  "Successfully deleted document 239401"
  ```

#### 11. `get_dp`
- **Description**: Lists all Data Provider identifiers (e.g. `DP0`, `DP1`) defined inside a Webi document.
- **Signature**: `get_dp(webi_doc_id: str) -> List[str]`
- **Example Response**:
  ```json
  ["DP0", "DP1"]
  ```

#### 12. `get_dp_details`
- **Description**: Fetches the underlying data source information for a specific Data Provider (e.g. underlying Universe ID, source type, and datasource name).
- **Signature**: `get_dp_details(webi_doc_id: str, dp_id: str) -> Optional[Dict[str, str]]`
- **Example Response**:
  ```json
  {
    "id": "DP0",
    "dataSourceId": "691420",
    "dataSourceType": "unx",
    "dataSourceName": "Financials UNX"
  }
  ```

#### 13. `purge_dp`
- **Description**: Purges all retrieved data rows from the specified data provider (`?purge=true`), reducing file size and clearing stale query results.
- **Signature**: `purge_dp(webi_doc_id: str, dp_id: str) -> str`
- **Example Response**:
  ```text
  "Successfully purged data provider DP0 from document 239401"
  ```

---

## Environment Variables

The server reads configuration from environment variables or a local `.env` file located in the project root:

| Variable | Required? | Default | Description | Example |
| :--- | :---: | :---: | :--- | :--- |
| `SAP_BO_REST_API_URL` | **Yes** | `None` (fallback: `http://ora-rhel-01.pf.box:8080/biprws`) | Full URL to SAP BI Platform REST Web Services (`biprws`) | `http://boserver.corp:8080/biprws` |
| `SAP_BO_USERNAME` | Optional | `None` | Default username for the `login` tool | `Administrator` |
| `SAP_BO_PASSWORD` | Optional | `None` | Default password for the `login` tool | `SecretP@ssw0rd` |

---

## Client Integration Guide

### 1. Google Antigravity IDE

Antigravity IDE discovers and registers MCP servers configured either at the **workspace level** or the **global user level**.

#### Option A: Workspace Configuration (Recommended for this project)

The project includes `.agents/mcp_config.json` in the root directory. When you open this folder in Antigravity IDE, the server is automatically discovered.

Verify that [`.agents/mcp_config.json`](file:///.agents/mcp_config.json) contains:

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

> [!TIP]
> If you are using a standard virtualenv instead of `uv`, you can point `command` directly to the interpreter:
> ```json
> {
>   "mcpServers": {
>     "sap-business-objects": {
>       "command": "/absolute/path/to/BO_MCP/.venv/bin/python",
>       "args": ["/absolute/path/to/BO_MCP/server.py"]
>     }
>   }
> }
> ```

#### Option B: Global Configuration (Available across all workspaces)

To use the SAP BO server in any workspace within Antigravity IDE, add it to your global configuration file:

**File path**: `~/.gemini/config/mcp_config.json`

```json
{
  "mcpServers": {
    "sap-business-objects": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/alessio/Insync/ballarin.alessio@gmail.com/GoogleDrive/programming/Python/MCP/BO_MCP",
        "run",
        "python",
        "server.py"
      ]
    }
  }
}
```

#### Verifying in Antigravity IDE

1. Open Antigravity IDE.
2. In the right-hand panel or menu, click **Additional Options (...) > MCP Servers**.
3. Confirm that `sap-business-objects` shows a green connected status and lists **13 tools**.
4. In the Sidebar Chat (Agent mode), you can now prompt the agent directly:
   - *"Accedi al server SAP BusinessObjects ed elencami tutti gli universi disponibili."*
   - *"Cerca tutti i report Web Intelligence collegati all'universo ID 582910 e mostrami i dettagli del primo report."*
   - *"Esegui il purge del data provider DP0 del report Webi 12345 e salvalo."*

---

### 2. Antigravity CLI (`agy`)

The terminal-based Antigravity CLI (`agy`) reads global customizations from `~/.gemini/config/mcp_config.json`.

#### Step 1: Configure `~/.gemini/config/mcp_config.json`

Add the server entry:

```json
{
  "mcpServers": {
    "sap-business-objects": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/alessio/Insync/ballarin.alessio@gmail.com/GoogleDrive/programming/Python/MCP/BO_MCP",
        "run",
        "python",
        "server.py"
      ]
    }
  }
}
```

#### Step 2: Launch `agy`

Open your terminal and run:

```bash
agy
```

#### Step 3: Use Tools in CLI

Once inside the interactive CLI session:

```text
> Login to SAP BusinessObjects and list the first 5 universes.
```

The agent will invoke `login()`, call `get_universes()`, and format the resulting list as a clean table in your terminal.

---

### 3. FastMCP Development Inspector (Web UI)

FastMCP includes an interactive browser-based development inspector where you can test tools without an AI client:

```bash
uv run fastmcp dev server.py
```

- This command starts the MCP server and launches a local web UI (usually at `http://localhost:5173` or `http://localhost:6274`).
- You can fill out form fields for tool arguments (e.g., test `login`, run `get_universes`, inspect `get_doc_details`) and view the raw JSON-RPC requests and responses.

---

### 4. Claude Desktop & Other MCP Hosts

For Anthropic Claude Desktop, add the configuration to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

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

---

## Available Scripts & Commands

| Command | Purpose |
| :--- | :--- |
| `uv sync` | Install or update dependencies from `uv.lock` |
| `uv run fastmcp inspect server.py` | Inspect the server and display tool counts and versions |
| `uv run fastmcp dev server.py` | Launch the interactive FastMCP Web Inspector for live debugging |
| `uv run python server.py` | Run the MCP server directly in STDIO mode |
| `uv run python -c "import server; print(server.mcp.name)"` | Quick import sanity test |

---

## Testing & Verification

### 1. Schema and Tool Check

Verify that all tools compile and validate:

```bash
uv run python -c "import server; print(f'Successfully loaded {len(server.mcp._tool_manager._tools)} tools on {server.mcp.name}')"
```

Expected output:
```text
Successfully loaded 13 tools on SAP Business Objects
```

### 2. Live Connection Test

You can test SAP BO connectivity directly in Python using `uv run python`:

```python
import os
from sdk_parser_new import BOESDKParser

# Initialize parser with your server parameters
parser = BOESDKParser(host='your-host', port='8080')

# Attempt login
parser.set_logon_token(os.getenv('SAP_BO_USERNAME'), os.getenv('SAP_BO_PASSWORD'))
print("Logon Token:", parser.logon_token)

# Retrieve universes
universes = parser.get_universes()
print(f"Retrieved {len(universes)} universes.")

# Clean logoff
parser.bo_logoff()
```

---

## Troubleshooting

### 1. `Login failed: Missing username or password`
- **Cause**: Environment variables `SAP_BO_USERNAME` or `SAP_BO_PASSWORD` are not defined in `.env`, or the file is missing.
- **Solution**: Copy `.env.example` to `.env` and fill in valid credentials.

### 2. `Could not log on and set the logon token!` (HTTP 401 / 500)
- **Cause**: Invalid SAP BO username or password, or the authentication service `/biprws/logon/long` rejected the request.
- **Solution**:
  - Verify your password does not contain unescaped characters.
  - Test reaching `http://<host>:<port>/biprws/logon/long` with a browser or `curl`.
  - Confirm the default authentication scheme (e.g. `secEnterprise`) is active on the server.

### 3. `Failed to get universes: Could not retrieve universes - have you set a valid logon token?`
- **Cause**: A tool was invoked before calling `login()`, or the SAP BO session expired.
- **Solution**: Call the `login` tool first. Sessions in SAP BO automatically expire after an inactivity timeout (typically 20-30 minutes).

### 4. SSL / InsecureRequestWarning Warnings
- **Cause**: The client uses `verify=False` to allow enterprise internal self-signed SSL certificates.
- **Solution**: This is expected for internal sandbox environments. For production environments with valid corporate root CA certificates, modify `verify=True` in `sdk_parser_new.py`.

### 5. `WSR 00999` Error
- **Cause**: Internal error in the Web Intelligence Processing Server (Raylight) when attempting to open a document that is corrupted, locked, or not a Webi document (e.g. Crystal Reports).
- **Solution**: `BOESDKParser.get_doc_status()` traps this error code. Verify that the target document ID corresponds to a Web Intelligence report.

### 6. Command Not Found: `uv`
- **Solution**: Install `uv` via `brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`. Alternatively, use `.venv/bin/python` directly.

---

## Security & Operational Best Practices

1. **Protect Credentials**: Never commit `.env` or hardcode passwords. Store production credentials in secure environment variables or vault systems.
2. **Dedicated Service Account**: Run this MCP server with a dedicated SAP BusinessObjects service user rather than personal administrative accounts.
3. **Destructive Operations Caution**: Tools like `delete_webi_doc` and `purge_dp` modify or remove data permanently in the CMS. Set appropriate InfoStore folder permissions for the MCP service user to restrict write access to authorized folders only.
4. **Network Boundaries**: Ensure the host running the MCP server has network access to port 8080 (or 6405 / 443 depending on your BIP deployment).

---

## Author & License

- **Author**: Alessio Ballarin
- **Version**: `0.1.0`
- **License**: Private / Internal Enterprise Use
