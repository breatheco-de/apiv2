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

    def __init__(self, token: str, refresh_token: Optional[str] = None):
        self._credentials = self._get_credentials(token, refresh_token)

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
            logger.info("Credentials created with token and refresh_token.")
            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Credentials refreshed.")
                except Exception as e:
                    logger.error(f"Failed to refresh credentials: {e}")
        elif os.path.exists(TOKEN_FILE_NAME):
            with open(TOKEN_FILE_NAME, "rb") as f:
                creds = pickle.load(f)
                logger.info("Credentials loaded from token file.")
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                        logger.info("Credentials refreshed from token file.")
                    except Exception as e:
                        logger.error(f"Failed to refresh credentials from token file: {e}")

        # If there are no valid credentials available, raise an exception
        if not creds or not creds.valid:
            raise Exception("Invalid or expired credentials. Please provide a valid token.")

        return creds

    async def get_user_info(self):
        if not self._credentials.valid:
            raise Exception("Invalid or expired credentials. Please provide a valid token.")

        logger.info(f"Access Token: {self._credentials.token}")
        logger.info(f"Token Expiry: {self._credentials.expiry}")
        logger.info(f"Refresh Token: {self._credentials.refresh_token}")

        # Check if the token is expired or about to expire and refresh if necessary
        if self._credentials.expired or not self._credentials.token:
            try:
                self._credentials.refresh(Request())
                logger.info("Credentials refreshed before making API call.")
            except Exception as e:
                logger.error(f"Failed to refresh credentials before making API call: {e}")
                raise

        service = build("oauth2", "v2", credentials=self._credentials)
        logger.info("Google API service built with credentials.")
        try:
            user_info = service.userinfo().get().execute()
            logger.info("User info retrieved successfully.")
            return user_info
        except Exception as e:
            logger.error(f"Failed to retrieve user info: {e}")
            raise
