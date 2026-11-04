# Central Management Server (CMS) Administration & Security Runbook

This reference provides technical instructions, syntax guidelines, and administration procedures for querying the CMS repository, auditing users and groups, and managing active sessions using `bo-mcp`.

---

## 1. Central Management Server (CMS) Query Engine

The `cms_query(query: str)` tool allows executing native CMS SQL queries against the SAP BO metadata repository.

### 1.1 CMS Virtual Tables
The CMS database organizes objects into three virtual tables:
* **`CI_INFOOBJECTS`**: Holds reports (Webi, Crystal), publications, instances, schedules, program objects, and folders.
* **`CI_SYSTEMOBJECTS`**: Holds administrative and security infrastructure objects: users (`SI_KIND = 'User'`), user groups (`SI_KIND = 'UserGroup'`), servers, server groups, licenses, and connection objects.
* **`CI_APPOBJECTS`**: Holds semantic layer assets: UNX Universes (`SI_KIND = 'DSL.MetaDataFile'`), legacy UNV Universes (`SI_KIND = 'Universe'`), and applications.

### 1.2 CMS SQL Rules & Limitations
Keep these rules in mind when formulating CMS queries:
1. **No JOIN Operations:** CMS SQL does not support table joins. Queries must target a single virtual table at a time.
2. **No GROUP BY or Aggregations:** CMS SQL does not support `COUNT()`, `GROUP BY`, `SUM()`, or `HAVING`.
3. **Single Quotes for Literals:** Strings must be enclosed in single quotes (e.g., `SI_KIND = 'Webi'`).
4. **Specific Projections:** Avoid `SELECT *`. Always select required attributes (e.g., `SELECT SI_ID, SI_NAME, SI_CUID, SI_KIND, SI_PARENTID ...`).
5. **Relationship Traversal:** To find related objects, run an initial query to retrieve IDs/CUIDs, then run a secondary query with an `IN (...)` clause.

### 1.3 Essential CMS Query Examples

* **Find Webi Reports in a Specific Folder:**
  ```sql
  SELECT SI_ID, SI_NAME, SI_CUID, SI_PARENTID, SI_UPDATE_TS
  FROM CI_INFOOBJECTS
  WHERE SI_KIND = 'Webi' AND SI_PARENTID = 12345
  ```

* **Find All Published Universes (UNX and UNV):**
  ```sql
  SELECT SI_ID, SI_NAME, SI_KIND, SI_CUID, SI_PARENTID
  FROM CI_APPOBJECTS
  WHERE SI_KIND IN ('DSL.MetaDataFile', 'Universe')
  ```

* **Find Failed Instances from the Last 24 Hours:**
  ```sql
  SELECT SI_ID, SI_NAME, SI_STARTTIME, SI_ENDTIME, SI_STATUSINFO
  FROM CI_INFOOBJECTS
  WHERE SI_SCHEDULE_STATUS = 3 AND SI_STARTTIME >= '2026-11-02 00:00:00'
  ORDER BY SI_STARTTIME DESC
  ```

* **Find Object by CUID:**
  ```sql
  SELECT SI_ID, SI_NAME, SI_KIND, SI_PARENTID
  FROM CI_INFOOBJECTS
  WHERE SI_CUID = 'AY.F4YfRzkpDvgF2W6Gk9eY'
  ```

---

## 2. User & Group Administration

### 2.1 Auditing Users
* **List Users:** Call `get_users()` to retrieve a list of all user accounts (`id`, `name`, `cuid`).
* **Inspect User Profile:** Call `get_user_details(user_id)` to view account status, email address, full name, and whether the account is disabled.

### 2.2 Auditing User Groups & Memberships
* **List Groups:** Call `get_user_groups()` to retrieve all configured user groups.
* **Inspect Group Members:** Call `get_group_users(group_id)` to list all members assigned to a specific group.

### 2.3 Account Status Management (Tier 2 Safeguard)
* **Disable/Enable Account:** `set_user_status(user_id, disabled: bool)`.
* **Required Confirmation Protocol:**
  - Before invoking `set_user_status`, verify the username and current status with `get_user_details`.
  - Present the username, ID, and requested action to the user:
    > "I am about to change user status for 'jdoe' (ID: 54321) to DISABLED. Please confirm if you wish to proceed."
  - Proceed only upon explicit affirmative user response.

---

## 3. Active Session Monitoring & Termination

### 3.1 Monitoring Active Sessions
* Call `get_active_sessions()` to retrieve all active logon sessions across the cluster.
* Review session attributes: `session_id`, `username`, `client_type`, `logon_time`.

### 3.2 Terminating Sessions (Tier 2 Safeguard)
* Used to free up enterprise user licenses or terminate orphaned/frozen client sessions.
* **Tool:** `terminate_session(session_id: str)`.
* **Required Confirmation Protocol:**
  - Locate session ID using `get_active_sessions()`.
  - Present session details (Username, Logon Time, Client Type, Session ID).
  - Explicit confirmation is mandatory before calling `terminate_session`.

---

## 4. Repository Hierarchy & Folders

### 4.1 Folder Navigation
* Call `get_folders()` to list root public folders.
* Call `get_folder_details(folder_id)` to inspect child folders and documents.
* Call `get_categories()` to inspect corporate taxonomy/category tags.

### 4.2 Folder Management (Tier 2 Safeguards)
* **Create Folder:** `create_folder(name: str, parent_folder_id: Optional[str] = None)`.
* **Delete Folder:** `delete_folder(folder_id: str)`.
  *Confirmation rule:* Always verify whether the folder contains active reports or child objects before requesting confirmation.

