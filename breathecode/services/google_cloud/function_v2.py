import logging, json, requests
from google.auth.transport.requests import Request as GCRequest
from google.oauth2 import id_token
from . import credentials

logger = logging.getLogger(__name__)

__all__ = ["FunctionV2"]


class FunctionV2:
    """Google Cloud Function handler"""

    service_url: str
    method: str

    def __init__(self, url, method="POST"):
        """
        Google Cloud Function constructor.

        Keywords arguments:
        - url(`str`): Google Cloud Function url.
        """

        credentials.resolve_credentials()
        self.service_url = url
        self.method = method

    def call(self, data=None, params=None, timeout=2) -> requests.models.Response:
        """
        Call a Google Cloud Function, return a `requests.models.Response` object.

        Keywords arguments:
        - data (`dict`): Arguments of Google Cloud Function.
        """

        if params is None:
            params = {}

        auth_req = GCRequest()
        token = id_token.fetch_id_token(auth_req, self.service_url)
        headers = {"Authorization": f"Bearer {token}"}

        if data:
            headers["Content-Type"] = "application/json"
            headers["Accept"] = "application/json"
            data = json.dumps(data)

        request = requests.request(
            self.method, self.service_url, data=data, headers=headers, params=params, timeout=timeout
        )

        logger.info(f"Cloud function {self.service_url}")
        logger.info(request.content.decode("utf-8"))

        return request


Function = FunctionV2
