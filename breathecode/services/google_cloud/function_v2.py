import logging, json, requests
from google.auth.transport.requests import Request as GCRequest
from . import credentials

logger = logging.getLogger(__name__)

__all__ = ['FunctionV2']


class FunctionV2:
    """Google Cloud Function handler"""
    client = None

    def __init__(self, url):
        """
        Google Cloud Function constructor.

        Keywords arguments:
        - url(`str`): Google Cloud Function url.
        """

        credentials.resolve_credentials()
        self.service_url = url

    def call(self, data=None) -> requests.models.Response:
        """
        Call a Google Cloud Function, return a `requests.models.Response` object.

        Keywords arguments:
        - data (`dict`): Arguments of Google Cloud Function.
        """
        from google.oauth2.id_token import fetch_id_token

        auth_req = GCRequest()
        id_token = fetch_id_token(auth_req, self.service_url)
        headers = {'Authorization': f'Bearer {id_token}'}

        if data:
            headers['Content-Type'] = 'application/json'
            headers['Accept'] = 'application/json'
            data = json.dumps(data)

        request = requests.post(self.service_url, data=data, headers=headers)

        logger.info(f'Cloud function {self.service_url}')
        logger.info(request.content.decode('utf-8'))

        return request


Function = FunctionV2
