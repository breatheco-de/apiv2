import logging
import os
import pickle
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

__all__ = ["GoogleApps"]

TOKEN_FILE_NAME = "google_cloud_oauth_token.pickle"
GOOGLE_CLIENT_SECRET = "client_secret.json"

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GoogleApps:
    """Wrapper for each endpoint that a multibillionaire company can't develop"""

    def __init__(self, id_token: str, refresh_token: Optional[str] = None):
        self._credentials = self._get_credentials(id_token, refresh_token)

    # def _get_credentials(
    #     self, token: Optional[str] = None, refresh_token: Optional[str] = None
    # ) -> Optional[Credentials]:
    #     creds = None

    #     if token:
    #         creds = Credentials(
    #             token=token,
    #             refresh_token=refresh_token,
    #             token_uri="https://oauth2.googleapis.com/token",
    #             client_id=os.getenv("GOOGLE_CLIENT_ID"),
    #             client_secret=os.getenv("GOOGLE_SECRET"),
    #         )
    #         logger.info("Credentials created with token and refresh_token.")
    #         if creds.expired and creds.refresh_token:
    #             try:
    #                 creds.refresh(Request())
    #                 logger.info("Credentials refreshed.")
    #             except Exception as e:
    #                 logger.error(f"Failed to refresh credentials: {e}")
    #     elif os.path.exists(TOKEN_FILE_NAME):
    #         with open(TOKEN_FILE_NAME, "rb") as f:
    #             creds = pickle.load(f)
    #             logger.info("Credentials loaded from token file.")
    #             if creds and creds.expired and creds.refresh_token:
    #                 try:
    #                     creds.refresh(Request())
    #                     logger.info("Credentials refreshed from token file.")
    #                 except Exception as e:
    #                     logger.error(f"Failed to refresh credentials from token file: {e}")

    #     # If there are no valid credentials available, raise an exception
    #     if not creds or not creds.valid:
    #         raise Exception("Invalid or expired credentials. Please provide a valid token.")

    #     return creds

    def _get_credentials(
        self, token: Optional[str] = None, refresh_token: Optional[str] = None
    ) -> Optional[Credentials]:
        creds = None

        if token:
            creds = Credentials(
                token=token,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=os.getenv("GOOGLE_CLIENT_ID"),
                client_secret=os.getenv("GOOGLE_SECRET"),
            )
            creds.refresh(Request())
        elif os.path.exists(TOKEN_FILE_NAME):
            with open(TOKEN_FILE_NAME, "rb") as f:
                creds = pickle.load(f)
                creds.refresh(Request())

        # If there are no valid credentials available, raise an exception
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                raise Exception("Invalid or expired credentials. Please provide a valid token.")

        return creds

    async def get_user_info(self):
        service = build("oauth2", "v2", credentials=self._credentials)
        return service.userinfo().get().execute()
