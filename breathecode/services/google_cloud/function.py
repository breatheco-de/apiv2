import logging, json, requests
from google.auth.transport.requests import Request as GCRequest
from .credentials import resolve_credentials

logger = logging.getLogger(__name__)


class Function:
    """Google Cloud Storage"""
    client = None

    def __init__(self, region, project_id, name):
        resolve_credentials()
        self.service_url = f'{region}-{project_id}.cloudfunctions.net/{name}'

    def call(self, data=None):
        from google.oauth2.id_token import fetch_id_token

        auth_req = GCRequest()
        id_token = fetch_id_token(auth_req, 'https://' + self.service_url)
        headers = {"Authorization": f"Bearer {id_token}"}

        if data:
            headers['Content-Type'] = 'application/json'
            headers['Accept'] = 'application/json'
            data = json.dumps(data)

        request = requests.post('https://' + self.service_url,
                                data=data,
                                headers=headers)

        logger.info(f'Cloud function {self.service_url}')
        logger.info(request.content.decode('utf-8'))

        res = request.json()
        return res
