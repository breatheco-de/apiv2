import logging, json, requests
from google.auth.transport.requests import Request as GCRequest
from google.oauth2 import id_token
from . import credentials

logger = logging.getLogger(__name__)

__all__ = ["Function", "FunctionV1"]


class FunctionV1:
    """Google Cloud Function handler."""

    service_url: str
    method: str

    def __init__(self, region, project_id, name, method="POST"):
        """Google Cloud Function constructor.

        Args:
            region (str): Google Cloud Function region
            project_id (str): Google Cloud Function project id
            name (str): Google Cloud Function name
        """

        credentials.resolve_credentials()
        self.service_url = f"{region}-{project_id}.cloudfunctions.net/{name}"
        self.method = method

    def call(self, data=None, params=None, timeout=2) -> requests.models.Response:
        """Call a Google Cloud Function.

        Args:
            data (dict): Arguments of Google Cloud Function.

        Returns:
            Response: Google Cloud Function response.
        """

        if params is None:
            params = {}

        auth_req = GCRequest()
        token = id_token.fetch_id_token(auth_req, "https://" + self.service_url)
        headers = {"Authorization": f"Bearer {token}"}

        if data:
            headers["Content-Type"] = "application/json"
            headers["Accept"] = "application/json"
            data = json.dumps(data)

        request = requests.request(
            self.method, "https://" + self.service_url, data=data, headers=headers, params=params, timeout=timeout
        )

        logger.info(f"Cloud function {self.service_url}")
        logger.info(request.content.decode("utf-8"))

        return request


Function = FunctionV1
