"""
Administration, Security, and CMS Query Service for SAP BusinessObjects 4.3 SP5.
Provides generic CMS SQL queries, User/Group management, RBAC group verification, and active session monitoring.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from core.client import BOEClient
from core.exceptions import BOEError, BOEQueryError

logger = logging.getLogger("AdminService")


class AdminService:
    """Service to handle administrative, security, and CMS repository querying operations."""

    def __init__(self, client: BOEClient):
        self.client = client

    # =========================================================================
    # 1. Central Management Server (CMS) Generic Query
    # =========================================================================

    def cms_query(self, query: str, page: int = 1, pagesize: int = 1000) -> Dict[str, Any]:
        """
        Executes an arbitrary SQL-like query against the CMS repository tables
        (CI_INFOOBJECTS, CI_APPOBJECTS, CI_SYSTEMOBJECTS).

        Example queries:
          - SELECT SI_ID, SI_NAME, SI_KIND FROM CI_INFOOBJECTS WHERE SI_KIND = 'Webi'
          - SELECT SI_ID, SI_NAME, SI_LASTLOGONTIME FROM CI_SYSTEMOBJECTS WHERE SI_KIND = 'User'
          - SELECT SI_ID, SI_NAME, SI_STATUSINFO FROM CI_INFOOBJECTS WHERE SI_SCHEDULE_STATUS = 3
        """
        url = f"{self.client.query_url}/cmsquery?page={page}&pagesize={pagesize}"
        payload = {"query": query}
        resp = self.client.post(url, json_data=payload)

        if isinstance(resp, dict):
            entries = resp.get("entries", [])
            return {
                "query": query,
                "page": page,
                "pagesize": pagesize,
                "total_returned": len(entries),
                "entries": entries,
            }
        raise BOEQueryError(f"CMS query failed: {resp}")

    # =========================================================================
    # 2. User Management
    # =========================================================================

    def get_users(self, page: int = 1, pagesize: int = 100) -> List[Dict[str, Any]]:
        """
        Lists user accounts in the BI platform repository (ID, Name, Full Name, Email, Disabled status).
        """
        query = (
            f"SELECT TOP {pagesize} SI_ID, SI_NAME, SI_DESCRIPTION, SI_EMAIL_ADDRESS, "
            f"SI_ACCOUNT_DISABLED, SI_LASTLOGONTIME FROM CI_SYSTEMOBJECTS WHERE SI_KIND = 'User' ORDER BY SI_NAME"
        )
        res = self.cms_query(query, page=page, pagesize=pagesize)
        users: List[Dict[str, Any]] = []

        for entry in res.get("entries", []):
            users.append(
                {
                    "id": str(entry.get("SI_ID", "")),
                    "username": str(entry.get("SI_NAME", "")),
                    "description": str(entry.get("SI_DESCRIPTION", "")),
                    "email": str(entry.get("SI_EMAIL_ADDRESS", "")),
                    "disabled": bool(entry.get("SI_ACCOUNT_DISABLED", False)),
                    "last_logon": str(entry.get("SI_LASTLOGONTIME", "")),
                }
            )
        return users

    def get_user_details(self, user_id: str) -> Dict[str, Any]:
        """
        Retrieves detailed profile properties for a specific user ID.
        """
        query = f"SELECT * FROM CI_SYSTEMOBJECTS WHERE SI_ID = {user_id} AND SI_KIND = 'User'"
        res = self.cms_query(query, page=1, pagesize=1)
        entries = res.get("entries", [])
        if entries:
            return entries[0]
        raise BOEError(f"User ID {user_id} not found in the CMS repository.")

    def set_user_status(self, user_id: str, disabled: bool) -> str:
        """
        Enables or disables a user account in the BI platform.
        """
        url = f"{self.client.bip_url}/v1/users/{user_id}"
        # SAP BO REST API allows updating user profile via PUT
        payload = {"entry": {"accountDisabled": disabled}}
        try:
            self.client.put(url, json_data=payload)
            action = "disabled" if disabled else "enabled"
            return f"User {user_id} successfully {action}."
        except Exception as e:
            # Provide actionable message if platform REST requires CMC console for specific security zones
            raise BOEError(f"Failed to update user status for {user_id}: {str(e)}")

    # =========================================================================
    # 3. User Groups, Membership & RBAC Verification
    # =========================================================================

    def get_user_groups(self, page: int = 1, pagesize: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieves all User Groups configured in the BI platform.
        """
        query = (
            f"SELECT TOP {pagesize} SI_ID, SI_NAME, SI_DESCRIPTION, SI_GROUP_MEMBERS "
            f"FROM CI_SYSTEMOBJECTS WHERE SI_KIND = 'UserGroup' ORDER BY SI_NAME"
        )
        res = self.cms_query(query, page=page, pagesize=pagesize)
        groups: List[Dict[str, Any]] = []

        for entry in res.get("entries", []):
            members_data = entry.get("SI_GROUP_MEMBERS", {})
            member_count = members_data.get("SI_TOTAL", 0) if isinstance(members_data, dict) else 0
            groups.append(
                {
                    "id": str(entry.get("SI_ID", "")),
                    "name": str(entry.get("SI_NAME", "")),
                    "description": str(entry.get("SI_DESCRIPTION", "")),
                    "members_count": member_count,
                }
            )
        return groups

    def get_group_users(self, group_id: str) -> List[Dict[str, str]]:
        """
        Retrieves all users that belong to a specific User Group.
        """
        query = (
            f"SELECT SI_ID, SI_NAME, SI_DESCRIPTION FROM CI_SYSTEMOBJECTS "
            f"WHERE SI_KIND = 'User' AND SI_USERGROUPS = {group_id} ORDER BY SI_NAME"
        )
        res = self.cms_query(query, page=1, pagesize=1000)
        users: List[Dict[str, str]] = []
        for entry in res.get("entries", []):
            users.append(
                {
                    "id": str(entry.get("SI_ID", "")),
                    "username": str(entry.get("SI_NAME", "")),
                    "description": str(entry.get("SI_DESCRIPTION", "")),
                }
            )
        return users

    def is_user_admin(self, username: str, admin_groups: Optional[List[str]] = None) -> bool:
        """
        Verifies whether a SAP BusinessObjects user holds Administrator privileges.
        Returns True if the username is 'Administrator' or belongs to any configured
        administrative UserGroup (defaults to 'Administrators' or SAP_BO_ADMIN_GROUPS).
        """
        normalized_user = (username or "").strip()
        if not normalized_user:
            return False

        # Built-in SAP BO Administrator account
        if normalized_user.lower() == "administrator":
            return True

        configured_groups = admin_groups
        if configured_groups is None:
            raw_env = os.getenv("SAP_BO_ADMIN_GROUPS", "Administrators")
            configured_groups = [g.strip() for g in raw_env.split(",") if g.strip()]

        try:
            for group_name in configured_groups:
                group_ids: List[str] = []
                if group_name.lower() == "administrators":
                    # Standard SAP BO Administrators group has SI_ID = 1, but also verify by name if customized
                    group_ids.append("1")
                escaped_group = group_name.replace("'", "''")
                grp_res = self.cms_query(
                    f"SELECT SI_ID, SI_NAME FROM CI_SYSTEMOBJECTS "
                    f"WHERE SI_KIND = 'UserGroup' AND SI_NAME = '{escaped_group}'",
                    page=1,
                    pagesize=10,
                )
                for entry in grp_res.get("entries", []):
                    gid = str(entry.get("SI_ID", "")).strip()
                    if gid and gid not in group_ids:
                        group_ids.append(gid)

                for gid in group_ids:
                    members = self.get_group_users(gid)
                    if any(m.get("username", "").strip().lower() == normalized_user.lower() for m in members):
                        return True
        except Exception as e:
            logger.warning(f"Failed to verify admin group membership for user '{normalized_user}': {e}")
            return False

        return False

    # =========================================================================
    # 4. Active Sessions Monitoring
    # =========================================================================

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """
        Monitors active sessions and open connections on the BI Platform Central Management Server.
        """
        query = (
            "SELECT SI_ID, SI_NAME, SI_AUTHEN_USER_NAME, SI_CREATION_TIME, SI_LASTLOGONTIME, SI_CLIENT_TYPE "
            "FROM CI_SYSTEMOBJECTS WHERE SI_KIND = 'Connection' ORDER BY SI_CREATION_TIME DESC"
        )
        res = self.cms_query(query, page=1, pagesize=500)
        sessions: List[Dict[str, Any]] = []

        for entry in res.get("entries", []):
            sessions.append(
                {
                    "connection_id": str(entry.get("SI_ID", "")),
                    "user_name": str(entry.get("SI_AUTHEN_USER_NAME") or entry.get("SI_NAME", "")),
                    "created_at": str(entry.get("SI_CREATION_TIME", "")),
                    "last_active": str(entry.get("SI_LASTLOGONTIME", "")),
                    "client_type": str(entry.get("SI_CLIENT_TYPE", "")),
                }
            )
        return sessions

    def terminate_session(self, session_id: str) -> str:
        """
        Terminates / logs off an active connection session from the CMS repository.
        """
        url = f"{self.client.bip_url}/v1/infostore/{session_id}"
        self.client.delete(url)
        return f"Session connection '{session_id}' successfully terminated."
