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

    def GetScenarios(self) -> List[str]:
        url = f'{self.api_url}/facility/scenarios'
        try:
            response = self.HttpGet(url)
            return self.ResponseToJson(response)['Scenarios']
        except: return []

    def CancelExecution(self, executionId: int):
        url = f'{self.api_url}/execution/{executionId}/cancel'
        response = self.HttpGet(url)
        return RestClient.ResponseToJson(response)
    
    def delete_test_case(self, test_case_name: str) -> Dict:
        url = f'{self.api_url}/facility/testcases/delete'
        payload = {"test_case_name": test_case_name}
        
        try:
            response = self.HttpPost(url, {'Content-Type': 'application/json'}, json.dumps(payload))
            return RestClient.ResponseToJson(response)
        except Exception as e:
            return {"error": f"Failed to delete test case: {str(e)}"}
        
    def upload_test_case(self, file):
        url = f"{self.api_url}/facility/upload_test_case"
        files = {'test_case': (file.filename, file.stream, file.content_type)}
        try:
            response = requests.post(url, files=files)
            return response.json()
        except Exception as e:
            return {"success": False, "message": f"Error sending test case: {str(e)}"}