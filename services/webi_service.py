"""
Web Intelligence (Webi) Service for SAP BusinessObjects 4.3 SP5.
Handles document lifecycle, prompt parameters, LOVs, refresh execution,
tabular data extraction from report blocks, data provider SQL, and formulas.
"""

from typing import List, Dict, Any, Optional, Union
import logging
from core.client import BOEClient
from core.exceptions import BOEError, BOEProcessingError

logger = logging.getLogger("WebiService")


class WebiService:
    """Service for Web Intelligence (Raylight) REST API operations."""

    def __init__(self, client: BOEClient):
        self.client = client

    # =========================================================================
    # 1. Document Lifecycle & Metadata
    # =========================================================================

    def get_documents(self, page: int = 1, pagesize: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieves a paginated list of Web Intelligence documents from the repository.
        """
        url = f"{self.client.webi_url}/documents?page={page}&pagesize={pagesize}"
        resp = self.client.get(url)
        docs: List[Dict[str, Any]] = []
        if isinstance(resp, dict) and "documents" in resp:
            raw_docs = resp["documents"].get("document", [])
            if isinstance(raw_docs, dict):
                raw_docs = [raw_docs]
            for doc in raw_docs:
                docs.append({
                    "id": str(doc.get("id", "")),
                    "cuid": str(doc.get("cuid", "")),
                    "name": str(doc.get("name", "")),
                    "folderId": str(doc.get("folderId", "")),
                    "updated": str(doc.get("updated", "")),
                })
        return docs

    def get_doc_details(self, webi_doc_id: str) -> Dict[str, Any]:
        """
        Gets document metadata: name, repository path, CUID, scheduled status, and state.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}"
        resp = self.client.get(url)
        if isinstance(resp, dict) and "document" in resp:
            doc = resp["document"]
            return {
                "webi_doc_id": str(doc.get("id", webi_doc_id)),
                "webi_doc_name": str(doc.get("name", "")),
                "webi_doc_path": str(doc.get("path", "")),
                "webi_doc_cuid": str(doc.get("cuid", "")),
                "webi_doc_scheduled": str(doc.get("scheduled", "false")).lower(),
                "webi_doc_state": str(doc.get("state", "")),
            }
        raise BOEError(f"Unable to read document details for ID {webi_doc_id}")

    def get_doc_properties(self, webi_doc_id: str) -> Dict[str, Any]:
        """
        Gets document properties (refreshOnOpen, usePersonalData, etc.).
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/properties"
        resp = self.client.get(url)
        if isinstance(resp, dict) and "properties" in resp:
            return resp["properties"]
        return {"raw": resp}

    def save_webi_doc(self, webi_doc_id: str, webi_doc_name: str, folder_id: int = -1) -> str:
        """
        Saves or overwrites a Webi document while preserving user comments and annotations.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}?overwrite=true&withComments=true"
        payload = {
            "document": {
                "name": webi_doc_name,
                "folderId": folder_id,
            }
        }
        self.client.post(url, json_data=payload)
        return f"Successfully saved document {webi_doc_id} as '{webi_doc_name}'"

    def delete_webi_doc(self, webi_doc_id: str) -> bool:
        """
        Permanently deletes a Webi document from the CMS repository.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}"
        self.client.delete(url)
        return True

    # =========================================================================
    # 2. Parameters, Prompts & Document Refresh
    # =========================================================================

    def get_doc_parameters(self, webi_doc_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all prompt parameters required by the Webi document.
        Returns a list of parameters with ID, prompt question, type, and optional flag.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/parameters"
        resp = self.client.get(url)
        parameters: List[Dict[str, Any]] = []

        if isinstance(resp, dict) and "parameters" in resp:
            raw_params = resp["parameters"].get("parameter", [])
            if isinstance(raw_params, dict):
                raw_params = [raw_params]
            for p in raw_params:
                param_info = {
                    "id": p.get("id"),
                    "name": p.get("name", ""),
                    "technicalName": p.get("technicalName", ""),
                    "type": p.get("type", ""),
                    "cardinality": p.get("cardinality", "Single"),
                    "optional": p.get("optional", False),
                    "constrained": p.get("constrained", False),
                }
                # Include current default answer if present
                if "answer" in p:
                    param_info["current_answer"] = p["answer"]
                parameters.append(param_info)

        return parameters

    def get_parameter_lov(self, webi_doc_id: str, parameter_id: Union[int, str], page: int = 1, pagesize: int = 100) -> List[Any]:
        """
        Retrieves the List of Values (LOV) allowed for a specific constrained parameter.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/parameters/{parameter_id}/values?page={page}&pagesize={pagesize}"
        resp = self.client.get(url)
        values: List[Any] = []
        if isinstance(resp, dict) and "values" in resp:
            val_items = resp["values"].get("value", [])
            if isinstance(val_items, dict):
                val_items = [val_items]
            for v in val_items:
                if isinstance(v, dict):
                    values.append(v.get("$") or v.get("@id") or v)
                else:
                    values.append(v)
        return values

    def refresh_webi_doc(
        self,
        webi_doc_id: str,
        parameters: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Refreshes the Webi document within the active session.
        If parameters are provided, submits prompt answers to trigger execution.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/parameters?refresh=true"
        payload: Dict[str, Any] = {}

        if parameters:
            formatted_params = []
            for p in parameters:
                p_id = p.get("id")
                p_val = p.get("value")
                if p_id is not None and p_val is not None:
                    # Support single value or list of values
                    if isinstance(p_val, list):
                        val_entries = [{"$": str(v)} for v in p_val]
                    else:
                        val_entries = [{"$": str(p_val)}]

                    formatted_params.append({
                        "id": p_id,
                        "answer": {
                            "values": {
                                "value": val_entries if len(val_entries) > 1 else val_entries[0]
                            }
                        }
                    })
            payload = {"parameters": {"parameter": formatted_params}}

        resp = self.client.put(url, json_data=payload if payload else None)
        return {
            "webi_doc_id": webi_doc_id,
            "status": "refreshed",
            "server_response": resp
        }

    # =========================================================================
    # 3. Data Providers & SQL Extraction
    # =========================================================================

    def get_dp(self, webi_doc_id: str) -> List[str]:
        """
        Lists all Data Provider identifiers (e.g. 'DP0', 'DP1') in a Webi document.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/dataproviders"
        resp = self.client.get(url)
        if isinstance(resp, dict) and "dataproviders" in resp:
            dps = resp["dataproviders"].get("dataprovider", [])
            if isinstance(dps, dict):
                dps = [dps]
            return [str(dp["id"]) for dp in dps if "id" in dp]
        return []

    def get_dp_details(self, webi_doc_id: str, dp_id: str) -> Dict[str, Any]:
        """
        Retrieves metadata and data source information for a specific Data Provider.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/dataproviders/{dp_id}"
        resp = self.client.get(url)
        if isinstance(resp, dict) and "dataprovider" in resp:
            dp_data = resp["dataprovider"]
            return {
                "id": str(dp_data.get("id", dp_id)),
                "dataSourceId": str(dp_data.get("dataSourceId", "")),
                "dataSourceType": str(dp_data.get("dataSourceType", "")),
                "dataSourceName": str(dp_data.get("dataSourceName", "")),
                "name": str(dp_data.get("name", "")),
                "isUpdated": dp_data.get("isUpdated", False),
            }
        raise BOEError(f"Data Provider {dp_id} not found in document {webi_doc_id}")

    def get_dp_specification(self, webi_doc_id: str, dp_id: str) -> Dict[str, Any]:
        """
        Retrieves the query specification (selected objects, query filters, sort order) of a Data Provider.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/dataproviders/{dp_id}/specification"
        resp = self.client.get(url)
        return resp if isinstance(resp, dict) else {"raw": resp}

    def get_dp_sql(self, webi_doc_id: str, dp_id: str) -> str:
        """
        Extracts the generated SQL query statement of a Data Provider.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/dataproviders/{dp_id}/queryplan"
        try:
            resp = self.client.get(url)
            if isinstance(resp, dict) and "queryplan" in resp:
                plan = resp["queryplan"]
                stmt = plan.get("statement", plan.get("sql", str(plan)))
                if isinstance(stmt, dict) and "$" in stmt:
                    return str(stmt["$"])
                elif isinstance(stmt, list):
                    return "\n\n".join([s.get("$", str(s)) if isinstance(s, dict) else str(s) for s in stmt])
                return str(stmt)
            return str(resp)
        except Exception:
            # Fallback: check details endpoint
            details = self.get_dp_details(webi_doc_id, dp_id)
            return details.get("sql", "SQL statement not directly exposed for this data provider type.")


    def refresh_dp(self, webi_doc_id: str, dp_id: str) -> str:
        """
        Refreshes a single Data Provider without refreshing the entire document.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/dataproviders/{dp_id}?refresh=true"
        resp = self.client.put(url)
        return f"Successfully refreshed data provider '{dp_id}' in document {webi_doc_id}"

    def purge_dp(self, webi_doc_id: str, dp_id: str) -> bool:
        """
        Purges all cached data from a specific Data Provider to reduce file size.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/dataproviders/{dp_id}?purge=true"
        self.client.put(url)
        return True

    # =========================================================================
    # 4. Reports (Tabs), Blocks & Tabular Data Extraction
    # =========================================================================

    def get_reports(self, webi_doc_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all sheets/tabs in a Web Intelligence document.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/reports"
        resp = self.client.get(url)
        reports: List[Dict[str, Any]] = []
        if isinstance(resp, dict) and "reports" in resp:
            raw_reports = resp["reports"].get("report", [])
            if isinstance(raw_reports, dict):
                raw_reports = [raw_reports]
            for r in raw_reports:
                reports.append({
                    "id": str(r.get("id", "")),
                    "name": str(r.get("name", "")),
                    "showWhenEmpty": r.get("showWhenEmpty", True),
                })
        return reports

    def get_report_elements(self, webi_doc_id: str, report_id: str) -> List[Dict[str, Any]]:
        """
        Lists all report elements (tables, charts, sections, forms) within a report tab.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/reports/{report_id}/elements"
        resp = self.client.get(url)
        elements: List[Dict[str, Any]] = []
        if isinstance(resp, dict) and "elements" in resp:
            raw_elems = resp["elements"].get("element", [])
            if isinstance(raw_elems, dict):
                raw_elems = [raw_elems]
            for el in raw_elems:
                elements.append({
                    "id": str(el.get("id", "")),
                    "name": str(el.get("name", "")),
                    "type": str(el.get("@type", el.get("type", ""))),
                })
        return elements

    def get_report_element_data(
        self,
        webi_doc_id: str,
        report_id: str,
        element_id: str,
        max_rows: int = 1000,
    ) -> Dict[str, Any]:
        """
        Extracts structured tabular data rows from a table or chart block in a report tab.
        Limits rows to max_rows (default 1000) to protect LLM token limits.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/reports/{report_id}/elements/{element_id}/data"
        try:
            resp = self.client.get(url)
        except Exception as e:
            return {
                "webi_doc_id": webi_doc_id,
                "report_id": report_id,
                "element_id": element_id,
                "total_rows_returned": 0,
                "columns": [],
                "data": [],
                "note": f"Element {element_id} does not expose a tabular dataset (it may be a layout cell, PageZone, or chart without table data): {str(e)}"
            }


        if not isinstance(resp, dict):
            return {"raw_data": str(resp)}

        # Parse Raylight dataset structure (columns / rows)
        dataset = resp.get("dataset", resp)
        rows_data: List[Dict[str, Any]] = []
        headers: List[str] = []

        # Extract column metadata
        if "columns" in dataset and "column" in dataset["columns"]:
            cols = dataset["columns"]["column"]
            if isinstance(cols, dict):
                cols = [cols]
            headers = [c.get("name") or c.get("@name") or f"Col_{i}" for i, c in enumerate(cols)]

        # Extract row values
        if "rows" in dataset and "row" in dataset["rows"]:
            raw_rows = dataset["rows"]["row"]
            if isinstance(raw_rows, dict):
                raw_rows = [raw_rows]

            for r_idx, r in enumerate(raw_rows[:max_rows]):
                cell_vals = r.get("cell", [])
                if isinstance(cell_vals, dict):
                    cell_vals = [cell_vals]

                row_dict: Dict[str, Any] = {}
                for c_idx, cell in enumerate(cell_vals):
                    val = cell.get("$") if isinstance(cell, dict) else str(cell)
                    col_name = headers[c_idx] if c_idx < len(headers) else f"Column_{c_idx+1}"
                    row_dict[col_name] = val
                rows_data.append(row_dict)

        return {
            "webi_doc_id": webi_doc_id,
            "report_id": report_id,
            "element_id": element_id,
            "total_rows_returned": len(rows_data),
            "columns": headers,
            "data": rows_data,
        }

    # =========================================================================
    # 5. Variables, Formulas & Comments
    # =========================================================================

    def get_variables(self, webi_doc_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all calculated variables and custom formulas defined in a Webi document.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/variables"
        resp = self.client.get(url)
        variables: List[Dict[str, Any]] = []
        if isinstance(resp, dict) and "variables" in resp:
            raw_vars = resp["variables"].get("variable", [])
            if isinstance(raw_vars, dict):
                raw_vars = [raw_vars]
            for v in raw_vars:
                variables.append({
                    "id": str(v.get("id", "")),
                    "name": str(v.get("name", "")),
                    "qualification": str(v.get("qualification", "")),
                    "formula": str(v.get("formula", "")),
                })
        return variables

    def create_variable(self, webi_doc_id: str, name: str, formula: str, qualification: str = "Dimension") -> Dict[str, Any]:
        """
        Creates a new calculated variable / formula in a Webi document.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/variables"
        payload = {
            "variable": {
                "name": name,
                "formula": formula,
                "qualification": qualification
            }
        }
        return self.client.post(url, json_data=payload)

    def delete_variable(self, webi_doc_id: str, variable_id: str) -> bool:
        """
        Deletes a variable from a Webi document.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/variables/{variable_id}"
        self.client.delete(url)
        return True

    def get_comments(self, webi_doc_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all collaborative user comments made on a Webi document.
        """
        url = f"{self.client.webi_url}/documents/{webi_doc_id}/comments"
        resp = self.client.get(url)
        comments: List[Dict[str, Any]] = []
        if isinstance(resp, dict) and "comments" in resp:
            raw_c = resp["comments"].get("comment", [])
            if isinstance(raw_c, dict):
                raw_c = [raw_c]
            for c in raw_c:
                comments.append({
                    "id": str(c.get("id", "")),
                    "author": str(c.get("author", "")),
                    "created": str(c.get("created", "")),
                    "content": str(c.get("content", "")),
                })
        return comments
