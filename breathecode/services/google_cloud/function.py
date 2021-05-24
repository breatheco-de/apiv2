import logging
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
        self.service_url = service_url

    def call(self, data=None):
        req = Request(self.service_url)

        auth_req = GCRequest()
        id_token = fetch_id_token(auth_req, self.service_url)

        req.add_header("Authorization", f"Bearer {id_token}")

        if data:
            req.add_header("Content-Type", 'application/json')

        response = urlopen(req, data)

        return response.read()
