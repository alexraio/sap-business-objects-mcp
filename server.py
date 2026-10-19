from fastmcp import FastMCP
from sdk_parser_new import BOESDKParser
from typing import List, Dict, Optional, Any
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

# Initialize the server
mcp = FastMCP("SAP Business Objects")

# Parse configuration
api_url = os.getenv("SAP_BO_REST_API_URL")
username_env = os.getenv("SAP_BO_USERNAME")
password_env = os.getenv("SAP_BO_PASSWORD")

# Initialize parser with configuration if available
if api_url:
    parsed_url = urlparse(api_url)
    protocol = parsed_url.scheme
    host = parsed_url.hostname
    port = str(parsed_url.port) if parsed_url.port else "8080"
    # Note: BOESDKParser constructs the full URL, so we just pass the components
    parser = BOESDKParser(protocol=protocol, host=host, port=port)
else:
    # Fallback to default
    parser = BOESDKParser()

@mcp.tool()
def login(username: str = None, password: str = None) -> str:
    """
    Log in to the SAP Business Objects platform.
    This must be called before using other tools.
    If username/password are not provided, uses environment variables.
    """
    user = username or username_env
    pwd = password or password_env
    
    if not user or not pwd:
        return "Login failed: Missing username or password. Please provide them or set SAP_BO_USERNAME and SAP_BO_PASSWORD in .env"

    try:
        parser.set_logon_token(user, pwd)
        return "Login successful"
    except Exception as e:
        return f"Login failed: {str(e)}"

@mcp.tool()
def logout() -> str:
    """Log out from the SAP Business Objects platform."""
    try:
        parser.bo_logoff()
        return "Logout successful"
    except Exception as e:
        return f"Logout failed: {str(e)}"

@mcp.tool()
def get_universes() -> List[Dict[str, str]]:
    """
    Retrieves a list of universes from the server.
    Returns a list of dictionaries with universe details (id, name, folderId).
    """
    try:
        universes = parser.get_universes()
        # Convert all values to strings to match the schema
        return [
            {
                'id': str(u['u_id']),
                'name': str(u['u_name']),
                'folderId': str(u['u_folderid'])
            }
            for u in universes
        ]
    except Exception as e:
        raise RuntimeError(f"Failed to get universes: {str(e)}")

@mcp.tool()
def get_universe_details(universe_id: str) -> Dict[str, str]:
    """
    Retrieves details of a specific universe.
    """
    try:
        return parser.get_univ_details(universe_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get universe details: {str(e)}")

@mcp.tool()
def get_universe_related_reports(universe_id: str) -> Dict[str, Any]:
    """
    Gets all reports related to a UNX or UNV universe.
    Returns a dictionary with universe ID, name, and a list of related reports.
    """
    try:
        u_id, u_name, reports = parser.get_universe_related_reports(universe_id)
        return {
            "universe_id": u_id,
            "universe_name": u_name,
            "reports": reports
        }
    except Exception as e:
        raise RuntimeError(f"Failed to get related reports: {str(e)}")

@mcp.tool()
def get_folders(folder_id: str) -> List[str]:
    """
    Gets all folders recursively starting from a root folder.
    Returns a list of folder IDs.
    """
    try:
        return parser.get_folders(folder_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get folders: {str(e)}")

@mcp.tool()
def get_webi_docs(folder_id: str) -> List[str]:
    """
    Gets all Webi documents in a folder.
    Returns a list of Webi document IDs.
    """
    try:
        return parser.get_webi_docs(folder_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get webi docs: {str(e)}")

@mcp.tool()
def get_doc_details(webi_doc_id: str) -> Optional[Dict[str, Any]]:
    """
    Gets document information (name, path, cuid, scheduled, state).
    """
    try:
        return parser.get_doc_details(webi_doc_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get doc details: {str(e)}")

@mcp.tool()
def delete_webi_doc(webi_doc_id: str) -> str:
    """
    Deletes a Webi document.
    """
    try:
        success = parser.delete_webi_doc(webi_doc_id)
        if success:
            return f"Successfully deleted document {webi_doc_id}"
        else:
            return f"Failed to delete document {webi_doc_id}"
    except Exception as e:
        return f"Error deleting document: {str(e)}"

@mcp.tool()
def save_webi_doc(webi_doc_id: str, webi_doc_name: str) -> str:
    """
    Saves or overwrites a Webi Document preserving comments.
    """
    try:
        parser.save_webi_doc(webi_doc_id, webi_doc_name)
        return f"Successfully saved document {webi_doc_id} as {webi_doc_name}"
    except Exception as e:
        return f"Error saving document: {str(e)}"

@mcp.tool()
def get_dp(webi_doc_id: str) -> List[str]:
    """
    Gets all Data Providers of a Webi document.
    Returns a list of Data Provider IDs.
    """
    try:
        return parser.get_dp(webi_doc_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get data providers: {str(e)}")

@mcp.tool()
def get_dp_details(webi_doc_id: str, dp_id: str) -> Optional[Dict[str, str]]:
    """
    Gets details of a specific Data Provider.
    """
    try:
        return parser.get_dp_details(webi_doc_id, dp_id)
    except Exception as e:
        raise RuntimeError(f"Failed to get data provider details: {str(e)}")

@mcp.tool()
def purge_dp(webi_doc_id: str, dp_id: str) -> str:
    """
    Purges a Data Provider of a Webi Document.
    """
    try:
        success = parser.purge_dp(webi_doc_id, dp_id)
        if success:
            return f"Successfully purged data provider {dp_id} from document {webi_doc_id}"
        else:
            return f"Failed to purge data provider {dp_id}"
    except Exception as e:
        return f"Error purging data provider: {str(e)}"

if __name__ == "__main__":
    mcp.run()
