'''
------------------------------------------------------

NAME:        
DESCRIPTION: Class to manage the connection to the Business Objects platform and perform operations on Webi documents.
AUTHOR:      Ballarin, Alessio
VERSION:     0.1
CREATED ON:  
CHANGED AT:  
CHANGES:     
0.1 -  - Initial version - Alessio Ballarin

------------------------------------------------------
'''

import requests
import json
import logging
import os
import datetime


class BOESDKParser:
    """
    This class interacts with a Business Objects platform using its REST API.
    It provides methods for logging in, retrieving universes, and managing 
    Webi documents, utilizing a session object for efficient connections.

    Attributes:
        protocol (str): Protocol used for the connection (default: 'http').
        host (str): Hostname of the Business Objects server (default: 'ora-rhel-01.pf.box').
        port (str): Port number of the Business Objects server (default: '8080').
        content_type (str): Content type for requests (default: 'application/json').
        bip_url (str): Base URL for the BI platform REST API.
        webi_url (str): URL for the Web Intelligence REST API.
        sl_url (str): URL for the Semantic Layer REST API.
        query_url (str): URL for the CMS query API.
        headers (dict): Default headers for requests.
        session (requests.Session): Session object for persistent connections.
        logon_token (str): Logon token for authentication.

    Example usage:
        >>> parser = BOESDKParser()
        >>> parser.set_logon_token('username', 'password')
        >>> universes = parser.get_universes()
        >>> print(universes)
    """

    def __init__(self, protocol='http', host='ora-rhel-01.pf.box', 
                 port='8080', content_type='application/json'):
        """
        Initializes the BOESDKParser with server details and creates a session.
        """
        base_url = f'{protocol}://{host}:{port}'
        self.bip_url = f'{base_url}/biprws'
        self.webi_url = f'{self.bip_url}/raylight/v1'
        self.sl_url = f'{self.bip_url}/sl/v1'
        self.query_url = f'{self.bip_url}/v1'
        self.headers = {
            'Accept': content_type,
            'Content-Type': content_type
        }
        self.session = requests.Session()
        self.logon_token = None

    def _get_auth_info(self):
        """
        Retrieves the login payload template for logon with user and password.

        Returns:
            requests.Response: Response object from the server.
        """
        url = f'{self.bip_url}/logon/long'
        return self.session.get(url, headers=self.headers, verify=False)

    def _get_trusted_token(self, username):
        """
        Retrieves the token with the trusted method.

        Args:
            username (str): Username for trusted authentication.

        Returns:
            requests.Response: Response object from the server.
        """
        url = f'{self.bip_url}/logon/trusted'
        headers = self.headers.copy()
        headers['X-SAP-TRUSTED-USER'] = username
        return self.session.get(url, headers=headers, verify=False)

    def _send_auth_info(self, username, password):
        """
        Retrieves a log in token using username and password.

        Args:
            username (str): Username for authentication.
            password (str): Password for authentication.

        Returns:
            requests.Response: Response object from the server.
        """
        payload = self._get_auth_info().json()
        payload['password'] = password
        payload['userName'] = username
        url = f'{self.bip_url}/logon/long'
        return self.session.post(url, json=payload, headers=self.headers, verify=False)

    def set_logon_token(self, username, password):
        """
        Sets the logon token in the headers for subsequent requests.

        Args:
            username (str): Username for authentication.
            password (str): Password for authentication.

        Raises:
            Exception: If the logon fails.
        """
        resp = self._send_auth_info(username, password)
        if resp.status_code == 200:
            resp_json = resp.json()
            self.logon_token = resp_json['logonToken']
            self.headers['X-SAP-LogonToken'] = self.logon_token
            logging.info(f"Logon successful, logon token set: {self.logon_token}")
        else:
            logging.error(f"Logon failed: {resp.status_code} - {resp.text}")
            raise Exception("Could not log on and set the logon token!")
        

    def set_trusted_token(self, username='Administrator'):
        """
        Sets the trusted token in the headers for subsequent requests.

        Args:
            username (str): Username for trusted authentication (default: 'Administrator').

        Raises:
            Exception: If the trusted logon fails.
        """
        resp = self._get_trusted_token(username)
        if resp.status_code == 200:
            resp_json = resp.json()
            self.logon_token = resp_json['logonToken']
            self.headers['X-SAP-LogonToken'] = self.logon_token
        else:
            raise Exception("Could not log on and set the logon token!")

    def bo_logoff(self):
        """
        Logs off from the Business Objects platform and closes the session.
        """
        url = f'{self.bip_url}/v1/logoff'
        resp = self.session.post(url, headers=self.headers, verify=False)
        print(f'Logoff Status Code: {resp.status_code}')
        self.session.close()

    def get_universes(self):
        """
        Retrieves a list of universes from the server.

        Returns:
            list: A list of dictionaries, each containing details of a universe.
                  Example: [{'u_id': '123', 'u_name': 'MyUniverse', 'u_folderid': '456'}]

        Raises:
            Exception: If the universes cannot be retrieved.
        """
        url = f'{self.webi_url}/universes'
        resp = self.session.get(url, headers=self.headers, verify=False)
        if resp.status_code == 200:
            universes_json = resp.json()
            return [{'u_id': u['id'], 'u_name': u['name'], 
                     'u_folderid': u['folderId']}
                    for u in universes_json['universes']['universe']]
        else:
            raise Exception("Could not retrieve universes - have you set a valid logon token?")

    def get_universe_related_reports(self, universe_id):
        """
        Gets all reports related to a UNX or UNV universe.

        Args:
            universe_id (str): ID of the universe.

        Returns:
            tuple: A tuple containing the universe ID, universe name, and a list of related reports.

        Raises:
            ValueError: If the universe type is invalid.
            Exception: If the reports cannot be retrieved.
        """
        universe_details = self.get_univ_details(universe_id)
        universe_type = universe_details['u_type']
        print(f"Finding all reports related to the universe type: {universe_type}")

        url = f"{self.query_url}/cmsquery?page=1&pagesize=50000"
        if universe_type == 'unx':
            payload = {
                "query": f"SELECT TOP 50000 SI_ID, SI_NAME, SI_SL_DOCUMENTS FROM CI_APPOBJECTS WHERE SI_KIND = 'DSL.MetaDataFile' AND SI_ID ={universe_id}"
            }
            report_field = 'SI_SL_DOCUMENTS'
        elif universe_type == 'unv':
            payload = {
                "query": f"SELECT TOP 50000 SI_ID, SI_NAME, SI_WEBI FROM CI_APPOBJECTS WHERE SI_KIND = 'Universe' AND SI_ID = {universe_id}"
            }
            report_field = 'SI_WEBI'
        else:
            raise ValueError("Invalid universe type")

        resp = self.session.post(url, json=payload, headers=self.headers, verify=False)
        if resp.status_code == 200:
            j_resp = resp.json()
            reports = [value for key, value in j_resp['entries'][0][report_field].items() 
                       if key != 'SI_TOTAL']
            return j_resp['entries'][0]['SI_ID'], j_resp['entries'][0]['SI_NAME'], reports
        else:
            raise Exception(f"Could not retrieve reports: {resp.status_code} - {resp.text}")

    def get_univ_details(self, universe_id):
        """
        Retrieves details of a universe.

        Args:
            universe_id (str): ID of the universe.

        Returns:
            dict: A dictionary containing details of the universe.
                  Example: {'u_type': 'unx', 'u_name': 'MyUniverse', 'u_cuid': 'abc123'}

        Raises:
            Exception: If the universe details cannot be retrieved.
        """
        url = f"{self.webi_url}/universes/{universe_id}"
        resp = self.session.get(url, headers=self.headers, verify=False)
        if resp.status_code == 200:
            univ_details_json = resp.json()
            universe_type = univ_details_json['universe']['type'].lower()
            return {
                'u_type': universe_type,
                'u_name': univ_details_json['universe']['name'],
                'u_cuid': univ_details_json['universe']['cuid']
            }
        else:
            raise Exception("Could not retrieve the universe. Check the Universe ID again")

    
    def delete_webi_doc(self, webi_doc_id):
        """
        Deletes a Webi document.

        Args:
            webi_doc_id (str): ID of the Webi document to delete.

        Returns:
            bool: True if the deletion is successful, False otherwise.
        """
        url = f"{self.webi_url}/documents/{webi_doc_id}"
        try:
            resp = self.session.delete(url, headers=self.headers, verify=False)
            resp.raise_for_status()
            print(f'Deleted Webi document {webi_doc_id} - Status Code: {resp.status_code}')
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error deleting Webi document: {e}")
            return False


    def get_univ_related_conn_id(self, universe_id):
        """
        Gets the connection ID of a universe.

        Args:
            universe_id (str): ID of the universe.

        Returns:
            str: The connection ID associated with the universe.

        Raises:
            Exception: If the connection ID cannot be retrieved.
        """
        url = f"{self.query_url}/cmsquery?page=1&pagesize=50000"
        payload = {
            "query": f"select SI_NAME, SI_SPECIFIC_KIND, SI_DATACONNECTION from ci_appobjects, ci_infoobjects where si_id={universe_id}"
        }
        resp = self.session.post(url, json=payload, headers=self.headers, verify=False)
        if resp.status_code == 200:
            return resp.json()['entries'][0]['SI_DATACONNECTION']['1']
        else:
            raise Exception("Could not retrieve connection ID")

    def get_folders(self, folder_id, folder_list=None):
        """
        Gets all folders recursively starting from a root folder.

        Args:
            folder_id (str): ID of the root folder.
            folder_list (list, optional): List to store folder IDs (default: None).

        Returns:
            list: A list of folder IDs.
        """
        if folder_list is None:
            folder_list = []
        url = f"{self.bip_url}/infostore/{folder_id}/children?type=Folder&page=1&pagesize=10000"
        resp = self.session.get(url, headers=self.headers, verify=False)
        if resp.status_code == 200:
            j_resp = resp.json()
            for entry in j_resp['entries']:
                folder_list.append(entry['id'])
                self.get_folders(entry['id'], folder_list)
        return folder_list

    def get_webi_docs(self, folder_id, webi_list=None):
        """
        Gets all Webi documents in a folder.

        Args:
            folder_id (str): ID of the folder.
            webi_list (list, optional): List to store Webi document IDs (default: None).

        Returns:
            list: A list of Webi document IDs.
        """
        if webi_list is None:
            webi_list = []
        url = f"{self.bip_url}/infostore/{folder_id}/children?type=Webi&page=1&pagesize=10000"
        resp = self.session.get(url, headers=self.headers, verify=False)
        if resp.status_code == 200:
            j_resp = resp.json()
            for entry in j_resp['entries']:
                webi_list.append(entry['id'])
        return webi_list

    def get_dp(self, webi_doc_id):
        """
        Gets all Data Providers of a Webi document.

        Args:
            webi_doc_id (str): ID of the Webi document.

        Returns:
            list: A list of Data Provider IDs.
                  Returns an empty list if there's an error.
        """
        url = f"{self.webi_url}/documents/{webi_doc_id}/dataproviders"
        try:
            resp = self.session.get(url, headers=self.headers, verify=False)
            resp.raise_for_status()
            j_response = resp.json()
            return [dp['id'] for dp in j_response['dataproviders']['dataprovider']]
        except requests.exceptions.RequestException as e:
            print(f"Error getting Data Providers: {e}")
            return []
    
    def get_dp_details(self, webi_doc_id, dp_id):
        """
        Gets details of a specific Data Provider.

        Args:
            webi_doc_id (str): ID of the Webi document.
            dp_id (str): ID of the Data Provider.

        Returns:
            dict: A dictionary containing Data Provider details.
                  Example: {'id': 'DP0', 'dataSourceId': '809161', 'dataSourceType': 'unx', 'dataSourceName': 'eFashion'}
                  Returns None if there's an error.
        """
        url = f"{self.webi_url}/documents/{webi_doc_id}/dataproviders/{dp_id}"
        try:
            resp = self.session.get(url, headers=self.headers, verify=False)
            resp.raise_for_status()
            j_response = resp.json()
            dp_data = j_response['dataprovider']
            return {
                'id': dp_data['id'],
                'dataSourceId': dp_data['dataSourceId'],
                'dataSourceType': dp_data['dataSourceType'],
                'dataSourceName': dp_data['dataSourceName']
            }
        except requests.exceptions.RequestException as e:
            print(f"Error getting Data Provider details: {e}")
            return None

    def purge_dp(self, webi_doc_id, dp_id):
        """
        Purges a Data Provider of a Webi Document.

        Args:
            webi_doc_id (str): ID of the Webi document.
            dp_id (str): ID of the Data Provider.

        Returns:
            bool: True if the purge is successful, False otherwise.
        """
        url = f"{self.webi_url}/documents/{webi_doc_id}/dataproviders/{dp_id}?purge=true"
        try:
            resp = self.session.put(url, headers=self.headers, verify=False)
            resp.raise_for_status()
            print(f'Purged {dp_id} from Webi report {webi_doc_id} - Status Code: {resp.status_code}')
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error purging Data Provider: {e}")
            return False

    def save_webi_doc(self, webi_doc_id, webi_doc_name):
        """
        Saves or overwrites a Webi Document preserving comments.

        Args:
            webi_doc_id (str): ID of the Webi document.
            webi_doc_name (str): Name of the Webi document.
        """
        url = f"{self.webi_url}/documents/{webi_doc_id}?overwrite=true&withComments=true"
        payload = {
            "document": {
                "name": webi_doc_name,
                "folderId": -1
            }
        }
        try:
            resp = self.session.post(url, json=payload, headers=self.headers, verify=False)
            resp.raise_for_status()
            print(f'Saved Webi document {webi_doc_id} - Status Code: {resp.status_code}')
        except requests.exceptions.RequestException as e:
            print(f"Error saving Webi document: {e}")

    def get_doc_details(self, webi_doc_id):
        """
        Gets document information and returns it as a dictionary.

        Args:
            webi_doc_id (str): ID of the Webi document. 

        Returns:
            dict: A dictionary containing document details.
                  Returns None if there's an error.
        """
        url = f"{self.webi_url}/documents/{webi_doc_id}"
        try:
            resp = self.session.get(url, headers=self.headers, verify=False)
            resp.raise_for_status()
            j_response = resp.json()
            return {
                'webi_doc_name': j_response['document']['name'],
                'webi_doc_path': j_response['document']['path'],
                'webi_doc_cuid': j_response['document']['cuid'],
                'webi_doc_scheduled': j_response['document']['scheduled'],
                'webi_doc_state': j_response['document']['state']
            }
        except requests.exceptions.RequestException as e:
            print(f"Error getting document info: {e}")
            return None
            
            
    # @Alessio - Would be better to check for 404 status code end return 404 instead of None. 
    # +Than I can check for 404 in the colling script. This is better because 404 tell that the document is not a webi but a crystal.
    def get_doc_status(self, webi_doc_id):
        """
        Gets document status and returns it as a dictionary.
        Checks for a specific 500 error ("WSR 00999").

        Args:
            webi_doc_id (str): ID of the Webi document.

        Returns:
            dict: A dictionary containing document status.
            str: Returns "WSR 00999" if a 500 error with that message occurs.
            None: Returns None if there's a different error.
        """
        url = f"{self.webi_url}/documents/{webi_doc_id}"
        try:
            resp = self.session.get(url, headers=self.headers, verify=False)
            resp.raise_for_status()
            j_response = resp.json()
            return {
                'webi_doc_state': j_response['document']['state']
            }
        except requests.exceptions.RequestException as e:
            if resp is not None and resp.status_code == 500:
                try:
                    error_json = resp.json()
                    if 'error' in error_json and 'error_code' in error_json['error'] and error_json['error']['error_code'] == "WSR 00999":
                        return "WSR 00999"
                except ValueError:
                    # Handle cases where the 500 response is not valid JSON
                    print(f"Error decoding 500 JSON response: {e}")
                    return None
            else:
                print(f"Error getting document info: {e}")
                return None    
