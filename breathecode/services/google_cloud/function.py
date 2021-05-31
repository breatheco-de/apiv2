import logging, json, requests
from urllib.request import Request, urlopen
from google.auth.transport.requests import Request as GCRequest
from google.oauth2.id_token import fetch_id_token
from .credentials import resolve_credentials


logger = logging.getLogger(__name__)


class Function:
    """Google Cloud Storage"""
    client = None

    def __init__(self, service_url):
        resolve_credentials()
        self.service_url = service_url.replace('https://', '').replace('http://', '')

    def call(self, data=None):
        auth_req = GCRequest()
        id_token = fetch_id_token(auth_req, self.service_url)
        headers = {"Authorization": f"bearer {id_token}"}

        if data:
            headers['Content-Type'] = 'application/json'

        request = requests.post('https://' + self.service_url, data=data, headers=headers)
        return (request.content, request.status_code)
