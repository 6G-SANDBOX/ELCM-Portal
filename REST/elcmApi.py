import json
from typing import Dict, List, Optional
from app.models import Experiment
from .restClient import RestClient
from Helper import Config
import requests

class ElcmApi(RestClient):
    def __init__(self):
        config = Config().ELCM
        super().__init__(config.Host, config.Port, "")

    def Run(self, experimentId: int) -> Dict:
        url = f'{self.api_url}/api/v0/run'
        response = self.HttpPost(url, {'Content-Type': 'application/json'},
                                 json.dumps(Experiment.query.get(experimentId).serialization()))
        return RestClient.ResponseToJson(response)

    def GetLogs(self, executionId: int) -> Dict:
        url = f'{self.api_url}/execution/{executionId}/logs'
        response = self.HttpGet(url)
        return RestClient.ResponseToJson(response)

    def GetPeerId(self, executionId: int) -> Optional[int]:
        url = f'{self.api_url}/execution/{executionId}/peerId'
        try:
            response = self.HttpGet(url)
            return RestClient.ResponseToJson(response)['RemoteId']
        except Exception: return None

    def GetUEs(self) -> Optional[List[str]]:
        url = f'{self.api_url}/facility/ues'
        try:
            response = self.HttpGet(url)
            return self.ResponseToJson(response)['UEs']
        except: return None

    def GetTestCases(self) -> Optional[List[Dict[str, object]]]:
        url = f'{self.api_url}/facility/testcases'
        try:
            response = self.HttpGet(url)
            return self.ResponseToJson(response)['TestCases']
        except: return None

    def GetTestCasesInfo(self, test_cases: List[str], ues: List[str]) -> Optional[Dict[str, Dict[str, List[str]]]]:
        url = f'{self.api_url}/facility/testcases/info'
        payload = {
            "TestCases": test_cases,
            "UEs": ues
        }
        try:
            response = self.HttpPost(url, {'Content-Type': 'application/json'}, json.dumps(payload))
            return self.ResponseToJson(response)
        except:
            return None

    def GetScenarios(self) -> List[str]:
        url = f'{self.api_url}/facility/scenarios'
        try:
            response = self.HttpGet(url)
            return self.ResponseToJson(response)['Scenarios']
        except: return []

    def CancelExecution(self, executionId: int):
        url = f'{self.api_url}/execution/{executionId}/cancel_execution_api'
        response = self.HttpGet(url)
        return RestClient.ResponseToJson(response)
    
    def delete_test_case(self, test_case_name: str, file_type: str = "testcase") -> Dict:
        url = f'{self.api_url}/facility/testcases/delete'
        payload = {"test_case_name": test_case_name, "file_type": file_type}
        
        try:
            response = self.HttpPost(url, {'Content-Type': 'application/json'}, json.dumps(payload))
            return RestClient.ResponseToJson(response)
        except Exception as e:
            return {"error": f"Failed to delete test case: {str(e)}"}
        
    def upload_test_case(self, file, file_type: str = "testcase"):
        url = f"{self.api_url}/facility/upload_test_case"
        files = {'test_case': (file.filename, file.stream, file.content_type)}
        data = {'file_type': file_type}
        try:
            response = requests.post(url, files=files, data=data)
            return response.json()
        except Exception as e:
            return {"success": False, "message": f"Error sending test case: {str(e)}"}
        
    def edit_test_case(self, file, file_type: str = "testcase"):
        url = f"{self.api_url}/facility/edit_test_case"
        files = {'test_case': (file.filename, file.stream, file.content_type)}
        data = {'file_type': file_type}
        try:
            response = requests.post(url, files=files, data=data)
            return response.json()
        except Exception as e:
            return {"success": False, "message": f"Error sending test case: {str(e)}"}
        
    def GetExecutionInfo(self, executionId: int) -> Optional[Dict[str, Dict[str, List[str]]]]:
        url = f'{self.api_url}/facility/execution/info'
        payload = {"ExecutionId": executionId}
        try:
            response = self.HttpPost(url, {'Content-Type': 'application/json'}, json.dumps(payload))
            return self.ResponseToJson(response)
        except Exception as e:
            return None
