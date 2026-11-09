import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_context, get_http_headers

from core.self_diagnostics import collect_server_diagnostics, configure_server_logging
from core.session import SessionManager, UserSession
from sdk_parser_new import BOESDKParser

logger = logging.getLogger("BOEServer")

# Load environment variables relative to this script directory
load_dotenv(Path(__file__).parent / ".env")
configure_server_logging()

# Initialize FastMCP Server
mcp = FastMCP("SAP Business Objects")

# Initialize SessionManager & Default Session
session_manager = SessionManager()
default_session = session_manager.get_or_create_session("default")
parser: BOESDKParser = default_session.parser

# Parse fallback configuration
api_url = os.getenv("SAP_BO_REST_API_URL")
username_env = os.getenv("SAP_BO_USERNAME")
password_env = os.getenv("SAP_BO_PASSWORD")


def get_active_session(require_admin: bool = False) -> UserSession:
    """
    Resolves the isolated UserSession for the current FastMCP tool invocation.
    - In local STDIO mode (or direct Python calls in unit tests), returns `default_session`
      bound to `server.parser`.
    - In remote HTTP / SSE / Streamable-HTTP mode, resolves `ctx.session_id` (or HTTP headers)
      to an isolated per-client UserSession in `session_manager` and supports `X-SAP-LogonToken`
      header pass-through.
    - When `require_admin=True`, enforces SAP BusinessObjects Administrator RBAC before returning.
    """
    headers = get_http_headers(include_all=True)
    session_id = headers.get("mcp-session-id") or headers.get("x-session-id")

    if not session_id:
        try:
            ctx = get_context()
            session_id = ctx.session_id or ctx.client_id
        except RuntimeError:
            session_id = None

    resolved_id = str(session_id) if session_id else "default"

    if resolved_id == "default" and not session_manager.remote_mode and not headers:
        default_session.parser = parser
        session = default_session
    else:
        session = session_manager.get_or_create_session(resolved_id)

    # Support HTTP header pass-through for remote enterprise gateways (Strategy B)
    header_token = headers.get("x-sap-logontoken")
    header_user = headers.get("x-sap-username")
    header_pwd = headers.get("x-sap-password")

    if header_token and session.parser.client.logon_token != header_token:
        session.parser.client.logon_token = header_token
        session.parser.client.headers["X-SAP-LogonToken"] = header_token
        if header_user:
            session.authenticated_user = header_user
            session.is_admin = True if header_user.strip().lower() == "administrator" else None
    elif header_user and header_pwd and not session.is_authenticated:
        try:
            session.authenticate(username=header_user, password=header_pwd)
        except Exception as e:
            logger.warning(f"Failed auto-login from headers for user '{header_user}': {e}")

    if require_admin:
        session.ensure_admin()

    return session


def get_active_parser(require_admin: bool = False) -> BOESDKParser:
    """Returns the BOESDKParser bound to the current active session."""
    return get_active_session(require_admin=require_admin).parser


# =============================================================================
# 1. Authentication Tools
# =============================================================================


@mcp.tool()
def login(username: Optional[str] = None, password: Optional[str] = None) -> str:
    """
    Log in to the SAP BusinessObjects BI Platform.
    Establishes an active enterprise session and acquires a logon token (X-SAP-LogonToken).
    If username/password are omitted in local STDIO mode, values from .env or OS Keyring are resolved automatically.
    In remote HTTP/SSE mode, explicit per-session credentials are required.
    """
    session = get_active_session(require_admin=False)
    active_parser = session.parser

    if session_manager.remote_mode and (not username or not password):
        return (
            "Login failed: In remote multi-tenant HTTP/SSE mode, explicit username and password "
            "must be provided for each client session."
        )

    resolved_creds = session_manager.credential_provider.get_credentials() if (not username or not password) else None

    user = username or (resolved_creds.username if resolved_creds else None) or os.getenv("SAP_BO_USERNAME")
    pwd = password or (resolved_creds.get_password() if resolved_creds else None) or os.getenv("SAP_BO_PASSWORD")

    if not user or not pwd:
        return (
            "Login failed: Missing credentials. Please provide username/password, "
            "configure .env, or run 'python server.py configure' to securely store credentials in your OS Keyring."
        )

    try:
        active_parser.set_logon_token(user, pwd)
        session.authenticated_user = user
        session.is_admin = True if user.strip().lower() == "administrator" else None
        return f"Login successful for user '{user}'"
    except Exception as e:
        return f"Login failed: {str(e)}"


@mcp.tool()
def logout() -> str:
    """
    Log out from the SAP BusinessObjects platform and invalidate the active session token.
    """
    session = get_active_session(require_admin=False)
    session.authenticated_user = None
    session.is_admin = None
    try:
        session.parser.bo_logoff()
        return "Logout successful"
    except Exception as e:
        return f"Logout failed: {str(e)}"


# =============================================================================
# 2. Semantic Layer & Universes
# =============================================================================


@mcp.tool()
def get_universes() -> List[Dict[str, str]]:
    """
    Retrieves all published Universes (UNX and UNV) from the BI platform.
    Returns a list of objects containing 'id', 'name', and 'folderId'.
    """
    try:
        universes = get_active_parser().get_universes()
        return [
            {
                "id": str(u["u_id"]),
                "name": str(u["u_name"]),
                "folderId": str(u["u_folderid"]),
            }
            for u in universes
        ]
    except Exception as e:
        raise RuntimeError(f"Failed to get universes: {str(e)}")


@mcp.tool()
def get_universe_details(universe_id: str) -> Dict[str, str]:
    """
    Retrieves detailed metadata of a specific Universe (engine type: 'unx' or 'unv', name, CUID).
    """
    try:
        return get_active_parser().get_univ_details(universe_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get universe details for ID {universe_id}: {str(e)}")


@mcp.tool()
def get_universe_structure(universe_id: str) -> Dict[str, Any]:
    """
    Retrieves the complete business layer hierarchy (classes, dimensions, measures, attributes)
    of a universe using the Semantic Layer REST API (/sl/v1/universes/{id}).
    """
    try:
        return get_active_parser().get_universe_structure(universe_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get universe structure: {str(e)}")


@mcp.tool()
def get_universe_related_reports(universe_id: str) -> Dict[str, Any]:
    """
    Queries the CMS to discover all Web Intelligence reports built on top of a specific universe.
    Returns universe ID, name, universe type, and the list of related Webi report IDs.
    """
    try:
        u_id, u_name, reports = get_active_parser().get_universe_related_reports(universe_id)
        return {
            "universe_id": u_id,
            "universe_name": u_name,
            "total_reports": len(reports),
            "reports": reports,
        }
    except Exception as e:
        raise RuntimeError(f"Failed to get related reports: {str(e)}")


@mcp.tool()
def get_universe_connection_id(universe_id: str) -> Optional[str]:
    """
    Retrieves the Data Connection ID associated with a Universe.
    """
    try:
        return get_active_parser().get_univ_related_conn_id(universe_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get connection ID: {str(e)}")


# =============================================================================
# 3. Web Intelligence Documents & Lifecycle
# =============================================================================


@mcp.tool()
def get_documents(page: int = 1, pagesize: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieves a paginated list of Web Intelligence documents from the repository.
    Returns document ID, CUID, name, folder ID, and last updated timestamp.
    """
    try:
        return get_active_parser().get_documents(page=page, pagesize=pagesize)
    except Exception as e:
        raise RuntimeError(f"Failed to list documents: {str(e)}")


@mcp.tool()
def get_doc_details(webi_doc_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves metadata of a Webi report (name, repository folder path, CUID, scheduled status, and state).
    """
    try:
        return get_active_parser().get_doc_details(webi_doc_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get doc details for {webi_doc_id}: {str(e)}")


@mcp.tool()
def get_doc_properties(webi_doc_id: str) -> Dict[str, Any]:
    """
    Retrieves document configuration properties (refreshOnOpen, usePersonalData, formatting locale).
    """
    try:
        return get_active_parser().webi.get_doc_properties(webi_doc_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get doc properties: {str(e)}")


@mcp.tool()
def save_webi_doc(webi_doc_id: str, webi_doc_name: Optional[str] = None) -> str:
    """
    Saves a Web Intelligence document in place (if webi_doc_name is omitted),
    or saves/overwrites it with a specified name (Save As). Preserves user comments and annotations.
    """
    try:
        return get_active_parser().save_webi_doc(webi_doc_id, webi_doc_name)
    except Exception as e:
        return f"Error saving document: {str(e)}"


@mcp.tool()
def delete_webi_doc(webi_doc_id: str) -> str:
    """
    Permanently deletes a Web Intelligence document from the repository.
    """
    try:
        success = get_active_parser().delete_webi_doc(webi_doc_id)
        if success:
            return f"Successfully deleted document {webi_doc_id}"
        return f"Failed to delete document {webi_doc_id}"
    except Exception as e:
        return f"Error deleting document: {str(e)}"


@mcp.tool()
def export_webi_doc(
    webi_doc_id: str,
    export_format: str = "pdf",
    report_id: Optional[str] = None,
    output_path: Optional[str] = None,
    refresh: bool = False,
) -> Dict[str, Any]:
    """
    Exports a Web Intelligence document or a specific report tab to PDF, Excel (.xlsx), or CSV.

    Args:
        webi_doc_id: ID of the Web Intelligence document to export.
        export_format: Target format: 'pdf', 'xlsx' (or 'excel'), 'csv', or 'all' to export all formats.
        report_id: Optional report tab ID. If omitted for PDF/Excel, exports the full document.
                   For CSV, if omitted, the first report tab is exported automatically.
        output_path: Optional destination file or directory path. If omitted, files are saved
                     in the 'exports/' directory.
        refresh: If True, refreshes all document data providers in-session before generating the export.

    Returns:
        Dict containing export metadata, status, target file path(s), and file size in bytes.
    """
    try:
        return get_active_parser().export_webi_doc(
            webi_doc_id=webi_doc_id,
            export_format=export_format,
            report_id=report_id,
            output_path=output_path,
            refresh=refresh,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to export document {webi_doc_id} as {export_format}: {str(e)}")


# =============================================================================
# 4. Webi Prompts, Parameters & Refresh
# =============================================================================


@mcp.tool()
def get_doc_parameters(webi_doc_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves all prompt parameters required by a Web Intelligence report.
    Returns parameter ID, prompt question/name, technical name, data type, and whether it is mandatory or optional.
    """
    try:
        return get_active_parser().get_doc_parameters(webi_doc_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get doc parameters for {webi_doc_id}: {str(e)}")


@mcp.tool()
def get_parameter_lov(webi_doc_id: str, parameter_id: int) -> List[Any]:
    """
    Retrieves the List of Values (LOV) allowed for a constrained prompt parameter in a Webi document.
    """
    try:
        return get_active_parser().get_parameter_lov(webi_doc_id, parameter_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get LOV for parameter {parameter_id}: {str(e)}")


@mcp.tool()
def refresh_webi_doc(webi_doc_id: str, parameters: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Refreshes a Web Intelligence document. If the report requires prompts, answers can be passed
    as a list of objects, e.g. [{"id": 0, "value": "2026"}, {"id": 1, "value": ["Region A", "Region B"]}].
    """
    try:
        return get_active_parser().refresh_webi_doc(webi_doc_id, parameters)
    except Exception as e:
        raise RuntimeError(f"Failed to refresh document {webi_doc_id}: {str(e)}")


# =============================================================================
# 5. Webi Tabs, Blocks & Tabular Data Extraction
# =============================================================================


@mcp.tool()
def get_reports(webi_doc_id: str) -> List[Dict[str, Any]]:
    """
    Lists all sheets/tabs in a Web Intelligence document (returns report IDs and tab names).
    """
    try:
        return get_active_parser().get_reports(webi_doc_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get reports for {webi_doc_id}: {str(e)}")


@mcp.tool()
def get_report_elements(webi_doc_id: str, report_id: str) -> List[Dict[str, Any]]:
    """
    Lists all visual and data elements (tables, charts, sections) inside a report sheet/tab.
    """
    try:
        return get_active_parser().get_report_elements(webi_doc_id, report_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get report elements: {str(e)}")


@mcp.tool()
def get_report_element_data(
    webi_doc_id: str,
    report_id: str,
    element_id: str,
    max_rows: int = 1000,
) -> Dict[str, Any]:
    """
    Extracts structured tabular data rows from a table or chart block in a report tab.
    Caps output to max_rows (default 1000) to protect LLM context windows.
    Returns column names and a list of dictionary rows.
    """
    try:
        return get_active_parser().get_report_element_data(webi_doc_id, report_id, element_id, max_rows=max_rows)
    except Exception as e:
        raise RuntimeError(f"Failed to extract element data: {str(e)}")


@mcp.tool()
def get_variables(webi_doc_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves all custom formulas and calculated variables defined inside a Webi document.
    """
    try:
        return get_active_parser().get_variables(webi_doc_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get variables: {str(e)}")


@mcp.tool()
def get_comments(webi_doc_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves collaborative user comments and cell annotations in a Webi document.
    """
    try:
        return get_active_parser().get_comments(webi_doc_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get comments: {str(e)}")


# =============================================================================
# 6. Data Providers & SQL
# =============================================================================


@mcp.tool()
def get_dp(webi_doc_id: str) -> List[str]:
    """
    Lists all Data Provider identifiers (e.g. 'DP0', 'DP1') within a Webi document.
    """
    try:
        return get_active_parser().get_dp(webi_doc_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get data providers: {str(e)}")


@mcp.tool()
def get_dp_details(webi_doc_id: str, dp_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves metadata of a specific Data Provider (data source name, ID, type, and update status).
    """
    try:
        return get_active_parser().get_dp_details(webi_doc_id, dp_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get data provider details: {str(e)}")


@mcp.tool()
def get_dp_sql(webi_doc_id: str, dp_id: str) -> str:
    """
    Extracts the generated SQL query statement of a Data Provider.
    """
    try:
        return get_active_parser().get_dp_sql(webi_doc_id, dp_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get SQL for data provider {dp_id}: {str(e)}")


@mcp.tool()
def get_dp_specification(webi_doc_id: str, dp_id: str) -> Dict[str, Any]:
    """
    Retrieves the query specification tree (result objects, query filters, sort rules) of a Data Provider.
    """
    try:
        return get_active_parser().webi.get_dp_specification(webi_doc_id, dp_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get data provider specification: {str(e)}")


@mcp.tool()
def refresh_dp(webi_doc_id: str, dp_id: str) -> str:
    """
    Refreshes a single Data Provider without recalculating the rest of the report.
    """
    try:
        return get_active_parser().refresh_dp(webi_doc_id, dp_id)
    except Exception as e:
        return f"Error refreshing data provider {dp_id}: {str(e)}"


@mcp.tool()
def purge_dp(webi_doc_id: str, dp_id: str) -> str:
    """
    Purges cached data rows from a specific Data Provider to reduce document storage size.
    """
    try:
        success = get_active_parser().purge_dp(webi_doc_id, dp_id)
        if success:
            return f"Successfully purged data provider {dp_id} from document {webi_doc_id}"
        return f"Failed to purge data provider {dp_id}"
    except Exception as e:
        return f"Error purging data provider: {str(e)}"


@mcp.tool()
def get_dp_mapping_proposal(
    webi_doc_id: str,
    dp_id: str,
    target_datasource_id: str,
    strategies: Optional[str] = "SameID,SamePath,SameName",
    resolve_names: bool = True,
) -> Dict[str, Any]:
    """
    Generates and evaluates a Change Data Source mapping proposal for a Data Provider.
    Simulates repointing a Web Intelligence query to a target universe (e.g. UNV to UNX or repointed UNX)
    and reports matching status ('Ok', 'Ambiguous', 'NotFound') for all objects.

    Mapping Strategies (evaluated in sequence):
      - SameID: Matches objects having identical unique IDs. Recommended for UNV->UNX converted via IDT (100% precision).
      - SamePath: Matches objects by full folder hierarchy path (e.g. [Folder]/[Subfolder]/[Object]). Distinguishes homonyms safely.
      - SameTechnicalName: Matches objects by underlying database column or technical field name.
      - SameName: Matches objects by display name across any folder reorganization.
      - CloseName: Fuzzy string distance matching (Levenshtein). Helpful for minor typos/casing, but caution recommended.

    Recommended default: 'SameID,SamePath,SameName'.
    """
    try:
        return get_active_parser().get_dp_mapping_proposal(
            webi_doc_id=webi_doc_id,
            dp_id=dp_id,
            target_datasource_id=target_datasource_id,
            strategies=strategies,
            resolve_names=resolve_names,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to generate mapping proposal: {str(e)}")


@mcp.tool()
def change_dp_datasource(
    webi_doc_id: str,
    dp_id: str,
    target_datasource_id: str,
    strategies: Optional[str] = "SameID,SamePath,SameName",
    custom_mappings: Optional[List[Dict[str, str]]] = None,
    save: bool = True,
) -> Dict[str, Any]:
    """
    Executes Change Data Source on a Web Intelligence Data Provider (e.g. migrating UNV to UNX or repointing universes).
    Generates mapping proposal using evaluated strategies, applies any custom mapping overrides,
    submits changes to Raylight, and optionally saves the document permanently in the repository.

    Parameters:
      webi_doc_id: ID of the Web Intelligence document.
      dp_id: Data Provider identifier (e.g. 'DP0').
      target_datasource_id: ID of the target universe (UNX or UNV).
      strategies: Comma-separated list of strategies (default: 'SameID,SamePath,SameName').
      custom_mappings: Optional list of explicit overrides, e.g. [{"source_id": "OBJ_147", "target_id": "OBJ_147"}].
      save: If True (default), permanently commits changes to the repository via in-place save.
    """
    try:
        return get_active_parser().change_dp_datasource(
            webi_doc_id=webi_doc_id,
            dp_id=dp_id,
            target_datasource_id=target_datasource_id,
            strategies=strategies,
            custom_mappings=custom_mappings,
            save=save,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to change data source: {str(e)}")


# =============================================================================
# 7. Central Management Server (CMS) Administration & Queries
# =============================================================================


@mcp.tool()
def cms_query(query: str, page: int = 1, pagesize: int = 1000) -> Dict[str, Any]:
    """
    Executes an arbitrary SQL-like query against the CMS repository tables
    (CI_INFOOBJECTS, CI_APPOBJECTS, CI_SYSTEMOBJECTS).
    Examples:
      - 'SELECT SI_ID, SI_NAME FROM CI_INFOOBJECTS WHERE SI_KIND = \"Webi\"'
      - 'SELECT SI_ID, SI_NAME, SI_LASTLOGONTIME FROM CI_SYSTEMOBJECTS WHERE SI_KIND = \"User\"'
    """
    try:
        return get_active_parser().cms_query(query, page=page, pagesize=pagesize)
    except Exception as e:
        raise RuntimeError(f"CMS query failed: {str(e)}")


@mcp.tool()
def get_users(page: int = 1, pagesize: int = 100) -> List[Dict[str, Any]]:
    """
    Lists user accounts in the BI platform repository (ID, username, email, disabled status, last logon).
    """
    try:
        return get_active_parser().get_users(page=page, pagesize=pagesize)
    except Exception as e:
        raise RuntimeError(f"Failed to list users: {str(e)}")


@mcp.tool()
def get_user_details(user_id: str) -> Dict[str, Any]:
    """
    Retrieves full profile properties of a specific user ID.
    """
    try:
        return get_active_parser().get_user_details(user_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get user details for {user_id}: {str(e)}")


@mcp.tool()
def set_user_status(user_id: str, disabled: bool) -> str:
    """
    Enables (disabled=False) or disables (disabled=True) a user account in the BI platform.
    """
    try:
        return get_active_parser().set_user_status(user_id, disabled)
    except Exception as e:
        return f"Error setting user status: {str(e)}"


@mcp.tool()
def get_user_groups(page: int = 1, pagesize: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieves all User Groups configured in the BI platform along with member counts.
    """
    try:
        return get_active_parser().get_user_groups(page=page, pagesize=pagesize)
    except Exception as e:
        raise RuntimeError(f"Failed to list user groups: {str(e)}")


@mcp.tool()
def get_group_users(group_id: str) -> List[Dict[str, str]]:
    """
    Lists all users that are members of a specific User Group.
    """
    try:
        return get_active_parser().get_group_users(group_id)
    except Exception as e:
        raise RuntimeError(f"Failed to list group users: {str(e)}")


@mcp.tool()
def get_active_sessions() -> List[Dict[str, Any]]:
    """
    Monitors active connections and user sessions currently open on the Central Management Server.
    """
    try:
        return get_active_parser().get_active_sessions()
    except Exception as e:
        raise RuntimeError(f"Failed to get active sessions: {str(e)}")


@mcp.tool()
def terminate_session(session_id: str) -> str:
    """
    Forcibly disconnects and terminates an active user session by connection ID.
    """
    try:
        return get_active_parser().terminate_session(session_id)
    except Exception as e:
        return f"Error terminating session {session_id}: {str(e)}"


# =============================================================================
# 8. Schedules & Instances Monitoring
# =============================================================================


@mcp.tool()
def get_doc_schedules(webi_doc_id: str) -> List[Dict[str, Any]]:
    """
    Lists scheduled execution rules defined for a Web Intelligence document.
    """
    try:
        return get_active_parser().get_doc_schedules(webi_doc_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get schedules: {str(e)}")


@mcp.tool()
def get_doc_instances(webi_doc_id: str, max_instances: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieves historical run instances of a Webi report, including execution status (Success, Failed, Running)
    and execution timestamps.
    """
    try:
        return get_active_parser().get_doc_instances(webi_doc_id, max_instances=max_instances)
    except Exception as e:
        raise RuntimeError(f"Failed to get instances: {str(e)}")


@mcp.tool()
def get_instance_details(instance_id: str) -> Dict[str, Any]:
    """
    Retrieves detailed diagnostic information for a specific instance run,
    including failure error messages and file sizes.
    """
    try:
        return get_active_parser().get_instance_details(instance_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get instance details: {str(e)}")


@mcp.tool()
def delete_instance(instance_id: str) -> str:
    """
    Deletes a historical report execution instance from the CMS repository.
    """
    try:
        success = get_active_parser().delete_instance(instance_id)
        if success:
            return f"Successfully deleted instance {instance_id}"
        return f"Failed to delete instance {instance_id}"
    except Exception as e:
        return f"Error deleting instance: {str(e)}"


# =============================================================================
# 9. InfoStore & Folders
# =============================================================================


@mcp.tool()
def get_folders(folder_id: str) -> List[str]:
    """
    Gets all subfolder IDs recursively starting from a root folder ID.
    """
    try:
        return get_active_parser().get_folders(folder_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get folders: {str(e)}")


@mcp.tool()
def get_folder_details(folder_id: str) -> Dict[str, Any]:
    """
    Retrieves metadata of a repository folder (name, CUID, parent ID, description).
    """
    try:
        return get_active_parser().get_folder_details(folder_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get folder details: {str(e)}")


@mcp.tool()
def create_folder(name: str, parent_folder_id: str, description: Optional[str] = None) -> Dict[str, Any]:
    """
    Creates a new folder in the InfoStore repository under a parent folder.
    """
    try:
        return get_active_parser().infostore.create_folder(name, parent_folder_id, description)
    except Exception as e:
        raise RuntimeError(f"Failed to create folder: {str(e)}")


@mcp.tool()
def delete_folder(folder_id: str) -> str:
    """
    Permanently deletes a folder from the InfoStore repository.
    """
    try:
        success = get_active_parser().infostore.delete_folder(folder_id)
        if success:
            return f"Successfully deleted folder {folder_id}"
        return f"Failed to delete folder {folder_id}"
    except Exception as e:
        return f"Error deleting folder: {str(e)}"


@mcp.tool()
def get_webi_docs(folder_id: str) -> List[str]:
    """
    Lists all Web Intelligence document IDs located directly inside a repository folder.
    """
    try:
        return get_active_parser().get_webi_docs(folder_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get webi docs: {str(e)}")


@mcp.tool()
def get_categories() -> List[Dict[str, str]]:
    """
    Lists all Corporate Categories defined in the BI platform repository.
    """
    try:
        return get_active_parser().get_categories()
    except Exception as e:
        raise RuntimeError(f"Failed to get categories: {str(e)}")


# =============================================================================
# 10. Intelligent Diagnostics & Batch Health Monitoring
# =============================================================================


@mcp.tool()
def diagnose_batch_failures(
    hours_back: int = 12,
    kind: str = "All",
    folder_id: Optional[str] = None,
    max_instances: int = 100,
) -> Dict[str, Any]:
    """
    Intelligent Diagnostics Agent: Scans, deduplicates, and diagnoses nocturnal batch execution failures
    for Web Intelligence reports and Publications (SI_SCHEDULE_STATUS = 3).

    Performs automated clustering by error signature and delivers a structured Root Cause Analysis (RCA)
    with up to 3 ranked probable causes and actionable remediation steps for the system administrator.

    Args:
        hours_back: Time window in hours to look back (default: 12, covering overnight runs).
        kind: Object type to analyze ('Webi', 'Publication', or 'All').
        folder_id: Optional InfoStore folder ID to restrict the diagnostic scan.
        max_instances: Maximum number of failed instances to fetch and sample (default: 100).

    Returns:
        Structured JSON dictionary matching BatchDiagnosticsReport contract with executive summary,
        cluster breakdown, and top-3 ranked causes with operational guidance.
    """
    try:
        report = get_active_parser().diagnostic.diagnose_batch(
            hours_back=hours_back,
            kind=kind,
            folder_id=folder_id,
            max_instances=max_instances,
        )
        return report.model_dump(mode="json")
    except Exception as e:
        raise RuntimeError(f"Intelligent diagnostics scan failed: {str(e)}")


# =============================================================================
# 11. Local SAP BusinessObjects Server Log Inspection (Admin-Only)
# =============================================================================


@mcp.tool()
def list_bo_logs(
    server_type: Optional[str] = None,
    hours_back: int = 24,
    max_files: int = 100,
) -> Dict[str, Any]:
    """
    [Admin-Only] Lists recent SAP BusinessObjects server trace log files (.glf, .log, .trc)
    on the co-located SAP BO host, ordered by modification time (newest first).

    Args:
        server_type: Optional server filter (e.g. 'WebiProcessingServer', 'AdaptiveJobServer', 'CMS', 'WACS').
        hours_back: Only include log files modified within the last N hours (default: 24).
        max_files: Maximum number of log file entries to return (default: 100).
    """
    try:
        return get_active_parser(require_admin=True).list_bo_logs(
            server_type=server_type,
            hours_back=hours_back,
            max_files=max_files,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to list SAP BO log files: {str(e)}")


@mcp.tool()
def search_bo_logs(
    pattern: str,
    server_type: Optional[str] = None,
    hours_back: int = 12,
    severity: Optional[str] = None,
    max_matches: int = 50,
) -> Dict[str, Any]:
    """
    [Admin-Only] Streams and searches local SAP BusinessObjects server log files (.glf, .log, .trc)
    in reverse order (newest lines first) for an error code (e.g. 'IES 10901', 'WIS 30553', 'ORA-01017'),
    CUID, document ID, or regex pattern without loading large log files into memory.

    Args:
        pattern: Error code, substring, or regular expression to search for.
        server_type: Optional server component filter (e.g. 'WebiProcessingServer', 'AdaptiveJobServer').
        hours_back: Scan log files modified within the last N hours (default: 12).
        severity: Optional severity filter ('Error', 'Fatal', 'Warning', 'Info', 'Debug').
        max_matches: Maximum number of matching log lines to return (default: 50).
    """
    try:
        return get_active_parser(require_admin=True).search_bo_logs(
            pattern=pattern,
            server_type=server_type,
            hours_back=hours_back,
            severity=severity,
            max_matches=max_matches,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to search SAP BO logs: {str(e)}")


@mcp.tool()
def get_bo_log_context(
    file_name: str,
    line_number: int,
    context_lines: int = 20,
) -> Dict[str, Any]:
    """
    [Admin-Only] Retrieves surrounding log lines before and after a specific 1-based line_number
    inside a local SAP BusinessObjects log file (.glf or .log) to inspect full stack traces.

    Args:
        file_name: Relative file name inside SAP_BO_LOG_DIR (as returned by list_bo_logs or search_bo_logs).
        line_number: Target 1-based line number to center the context window around.
        context_lines: Number of lines before and after line_number to retrieve (default: 20, max: 200).
    """
    try:
        return get_active_parser(require_admin=True).get_bo_log_context(
            file_name=file_name,
            line_number=line_number,
            context_lines=context_lines,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to retrieve SAP BO log context: {str(e)}")


# =============================================================================
# 12. SAP BusinessObjects Auditing Database ODBC Introspection (Admin-Only)
# =============================================================================


@mcp.tool()
def get_audit_failed_events(
    hours_back: int = 24,
    event_type_id: Optional[int] = None,
    max_rows: int = 100,
) -> Dict[str, Any]:
    """
    [Admin-Only] Queries the SAP BusinessObjects Auditing Database (ADS_EVENT) via ODBC
    to retrieve failed platform events (non-zero Status_ID or populated Error_Code).

    Args:
        hours_back: Lookback window in hours (default: 24).
        event_type_id: Optional SAP BO Event_Type_ID filter (e.g. 1002=View, 1003=Refresh, 1011=Run, 1014=Logon).
        max_rows: Maximum number of audit rows to return (default: 100, max: 1000).
    """
    try:
        return get_active_parser(require_admin=True).get_audit_failed_events(
            hours_back=hours_back,
            event_type_id=event_type_id,
            max_rows=max_rows,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to query failed events from Auditing DB: {str(e)}")


@mcp.tool()
def get_audit_heavy_reports(
    days_back: int = 7,
    top_n: int = 20,
) -> Dict[str, Any]:
    """
    [Admin-Only] Queries the SAP BusinessObjects Auditing Database (ADS_EVENT) via ODBC
    to identify the slowest and heaviest reports over the last N days ranked by execution duration.

    Args:
        days_back: Number of days to analyze (default: 7).
        top_n: Number of top slowest reports to return (default: 20, max: 100).
    """
    try:
        return get_active_parser(require_admin=True).get_audit_heavy_reports(
            days_back=days_back,
            top_n=top_n,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to query heavy reports from Auditing DB: {str(e)}")


@mcp.tool()
def get_audit_user_activity(
    username: Optional[str] = None,
    hours_back: int = 24,
    max_rows: int = 100,
) -> Dict[str, Any]:
    """
    [Admin-Only] Queries the SAP BusinessObjects Auditing Database (ADS_EVENT) via ODBC
    to inspect recent user logon, document viewing, refresh, and export activity.

    Args:
        username: Optional SAP BO username filter. If omitted, returns activity across all users.
        hours_back: Lookback window in hours (default: 24).
        max_rows: Maximum number of audit rows to return (default: 100, max: 1000).
    """
    try:
        return get_active_parser(require_admin=True).get_audit_user_activity(
            username=username,
            hours_back=hours_back,
            max_rows=max_rows,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to query user activity from Auditing DB: {str(e)}")


@mcp.tool()
def query_audit_db(
    sql_query: str,
    max_rows: int = 200,
) -> Dict[str, Any]:
    """
    [Admin-Only] Executes a custom, strictly read-only SELECT (or WITH ... SELECT) SQL query
    against the SAP BusinessObjects Auditing Database (ADS_* tables) via ODBC.
    Multi-statement queries and any mutating/DDL keywords are blocked by a SQL security guardrail.

    Args:
        sql_query: Read-only SELECT SQL statement against ADS_EVENT, ADS_EVENT_DETAIL, etc.
        max_rows: Maximum number of rows to fetch and return (default: 200, max: 1000).
    """
    try:
        return get_active_parser(require_admin=True).query_audit_db(
            sql_query=sql_query,
            max_rows=max_rows,
        )
    except Exception as e:
        raise RuntimeError(f"Auditing DB query failed: {str(e)}")


# =============================================================================
# 13. MCP Server Self-Diagnostics & Remote Troubleshooting
# =============================================================================


@mcp.tool()
def get_mcp_server_diagnostics(
    include_recent_logs: bool = True,
    max_log_lines: int = 50,
) -> Dict[str, Any]:
    """
    Executes a non-destructive self-diagnostic health check on the MCP server host.
    Probes all 4 server subsystems and returns secret-masked telemetry so AI agents can
    troubleshoot remote HTTP/SSE deployments directly over MCP:
      1. Runtime environment (OS, Python version, process user, transport mode, active sessions, RBAC status)
      2. SAP BO REST API (`biprws/logon/long` HTTP reachability and latency in ms)
      3. Local SAP BO Log Directory (`SAP_BO_LOG_DIR` existence, read permissions, and recent `.glf` count)
      4. Auditing Database ODBC (`pyodbc` installation, available ODBC drivers, `ODBCINI`, and live SQL ping)
      5. Recent internal `bo-mcp` server logs and tracebacks from the in-memory ring buffer.

    Args:
        include_recent_logs: Whether to include recent internal MCP server log lines (default: True).
        max_log_lines: Maximum number of recent internal log lines to return (default: 50, max: 200).
    """
    session = get_active_session(require_admin=False)
    return collect_server_diagnostics(
        session=session,
        session_manager=session_manager,
        include_recent_logs=include_recent_logs,
        max_log_lines=max_log_lines,
    )


def parse_server_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parses CLI arguments for MCP transport mode and network binding."""
    arg_parser = argparse.ArgumentParser(description="SAP BusinessObjects BI Platform 4.3 SP5 MCP Server")
    arg_parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http", "http"],
        default=os.getenv("MCP_TRANSPORT", "stdio").strip().lower(),
        help="MCP transport protocol (default: stdio or MCP_TRANSPORT env var)",
    )
    arg_parser.add_argument(
        "--host",
        default=os.getenv("MCP_HOST", "0.0.0.0").strip(),
        help="Bind host for HTTP/SSE transport (default: 0.0.0.0 or MCP_HOST env var)",
    )
    arg_parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_PORT", "8000")),
        help="Bind port for HTTP/SSE transport (default: 8000 or MCP_PORT env var)",
    )
    return arg_parser.parse_args(argv)


def run_server(argv: Optional[List[str]] = None) -> None:
    """Main entry point dispatching credential CLI commands or starting the FastMCP server."""
    args_list = sys.argv[1:] if argv is None else argv

    # Support CLI subcommands for credential management and self-diagnostics
    if len(args_list) > 0 and args_list[0] == "doctor":
        import json

        report = collect_server_diagnostics(
            session=default_session,
            session_manager=session_manager,
            include_recent_logs=True,
        )
        print(json.dumps(report, indent=2))
        sys.exit(0)

    if len(args_list) > 0 and args_list[0] in ("configure", "setup", "test", "clear", "status"):
        from core.auth.cli import main as auth_cli_main

        sys.exit(auth_cli_main(args_list))

    parsed = parse_server_args(args_list)
    if parsed.transport in ("sse", "streamable-http", "http"):
        session_manager.remote_mode = True
        session_manager.start_background_cleanup(interval_seconds=300)
        mcp.run(transport=parsed.transport, host=parsed.host, port=parsed.port)
    else:
        session_manager.remote_mode = False
        mcp.run()


if __name__ == "__main__":
    run_server()
