# Batch Diagnostics, Schedules & Error Triage Runbook

This reference provides procedures for diagnosing nocturnal batch execution failures, auditing report schedules, and triaging SAP BusinessObjects error codes using `bo-mcp`.

---

## 1. Automated Batch Failure Diagnostics

The `diagnose_batch_failures(hours_back: int = 24, max_failures: int = 50)` tool performs automated root cause analysis (RCA) on failed scheduled instances (`SI_SCHEDULE_STATUS = 3`) across Web Intelligence reports and Publications.

### 1.1 Running the Diagnostic Scan
```python
# Default scan of the last 24 hours
diagnose_batch_failures(hours_back=24, max_failures=50)

# Deeper weekend / multi-day scan
diagnose_batch_failures(hours_back=72, max_failures=100)
```

### 1.2 Interpreting Diagnostic Output
The tool produces a structured Pydantic v2 payload containing:
* **`total_failures`**: Total count of failed instances within the time window.
* **`unique_signatures`**: Number of distinct error patterns identified.
* **`clusters`**: Array of failure clusters grouped by normalized error signature:
  - `error_signature`: Normalized error message (e.g., `IES 10901: Cannot connect to the relational database`).
  - `failure_count`: Number of reports impacted by this specific error.
  - `impacted_documents`: List of affected reports (`document_id`, `name`, `instance_id`, `start_time`).
  - `ranked_probable_causes`: Up to 3 ranked probable causes based on error heuristics.
  - `recommended_remediation_steps`: Actionable administrator instructions.

---

## 2. Common SAP BO Error Code Taxonomy & Triage Guide

When analyzing batch or interactive execution failures, follow this classification:

### 2.1 `IES 10901`: Cannot Connect to the Relational Database
* **Meaning:** The Data Federation Service or Webi Processing Server failed to establish a database socket handshake.
* **Triage Sequence:**
  1. **OS/Network Verification:** Check network routing and firewall rules from the SAP BO server hosting the Adaptive Job Server / Webi Processing Server to the target database host (e.g. `nc -zv <db_host> <db_port>`).
  2. **Semantic Layer Connection Test (MANDATORY RULE):**
     - **NEVER** instruct administrators to test relational connections in the CMC (the CMC has no test connection button for relational connections).
     - Instruct the administrator to test the relational connection (`.cnx` or `.cns`) using **Information Design Tool (IDT)**:
       1. Open IDT and connect to the CMS repository.
       2. Open the relational connection and click **Test Connection**.
     - For legacy `.unv` connections, test via **Universe Design Tool (UDT)**.
  3. **Database Driver Check:** Ensure 64-bit database client drivers are correctly configured on the SAP BO cluster nodes.

### 2.2 `WIS 30553` / `WIS 30551`: Server Error / Timeout
* **Meaning:** The Web Intelligence Processing Server terminated unexpectedly or timed out during calculation or data streaming.
* **Triage Sequence:**
  1. Inspect document complexity, recursive calculation formulas, and volume of extracted rows.
  2. In the Central Management Console (CMC), inspect **Servers -> Web Intelligence Processing Server**:
     - Check memory threshold limits (Maximum Memory Threshold).
     - Check timeout settings (Connection Timeout, Server Polling Time).
  3. Consider splitting large queries into smaller chunks or increasing server resource allocations.

### 2.3 `ORA-01017` / RDBMS Bad Credentials
* **Meaning:** Invalid username/password logon denied by the underlying database engine.
* **Triage Sequence:**
  1. The database service account password has expired or changed.
  2. Open the connection in **Information Design Tool (IDT)**.
  3. Update credentials and verify connection validity with **Test Connection**.
  4. Publish the updated connection back to the CMS repository.

### 2.4 `FWM 02024` / FRS Disk Space or File Access Error
* **Meaning:** File Repository Server (Input/Output FRS) cannot read the template or write the generated instance output.
* **Triage Sequence:**
  1. Verify disk space on the Input and Output FRS file storage volumes.
  2. Check OS permissions for the service account running the SAP BO platform.

---

## 3. Schedules & Instance Lifecycle Management

### 3.1 Auditing Document Schedules
* Call `get_doc_schedules(document_id)` to inspect:
  - Recurrence rules (Daily, Weekly, Monthly, Event-driven).
  - Prompts and parameter values passed during scheduling.
  - Destination settings (Default Enterprise Inbox, Email/SMTP, FTP, Local FileSystem).

### 3.2 Inspecting Historical Instances
* Call `get_doc_instances(document_id)` to list all historical instances:
  - Check status: `Success`, `Failed`, or `Running`.
  - Check instance IDs and completion timestamps.
* Call `get_instance_details(instance_id)`:
  - Retrieves exact error log and status text stored in `SI_STATUSINFO`.

### 3.3 Instance Cleanup (Tier 2 Safeguard)
* Call `delete_instance(instance_id)` to delete an instance.
* **Required Confirmation Protocol:**
  - Before calling `delete_instance`, confirm the parent document name, instance ID, and completion date with the user.

