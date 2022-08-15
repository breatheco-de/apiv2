import logging, json, requests
from google.auth.transport.requests import Request as GCRequest
from . import credentials

logger = logging.getLogger(__name__)

__all__ = ['Function', 'FunctionV1']


class FunctionV1:
    """Google Cloud Function handler"""
    client = None

    def __init__(self, region, project_id, name):
        """Google Cloud Function constructor
            Args:
                region (str): Google Cloud Function region
                project_id (str): Google Cloud Function project id
                name (str): Google Cloud Function name
        """

        credentials.resolve_credentials()
        self.service_url = f'{region}-{project_id}.cloudfunctions.net/{name}'

    def call(self, data=None) -> requests.models.Response:
        """Call a Google Cloud Function
            Args:
                data (dict): Arguments of Google Cloud Function.

            Returns:
                Response: Google Cloud Function response.
        """
        from google.oauth2.id_token import fetch_id_token

        auth_req = GCRequest()
        id_token = fetch_id_token(auth_req, 'https://' + self.service_url)
        headers = {'Authorization': f'Bearer {id_token}'}

        if data:
            headers['Content-Type'] = 'application/json'
            headers['Accept'] = 'application/json'
            data = json.dumps(data)

        request = requests.post('https://' + self.service_url, data=data, headers=headers)

        logger.info(f'Cloud function {self.service_url}')
        # logger.info(request.content.decode('utf-8'))

        return request


Function = FunctionV1
