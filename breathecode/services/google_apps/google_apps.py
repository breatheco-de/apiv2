import logging
import os
import pickle
from typing import Literal, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

__all__ = ["GoogleApps"]

TOKEN_FILE_NAME = "google_cloud_oauth_id_token.pickle"
GOOGLE_CLIENT_SECRET = "client_secret.json"

logger = logging.getLogger(__name__)


type MeetEventType = Literal[
    "google.workspace.meet.conference.v2.started",
    "google.workspace.meet.conference.v2.ended",
    "google.workspace.meet.participant.v2.joined",
    "google.workspace.meet.participant.v2.left",
    "google.workspace.meet.recording.v2.fileGenerated",
    "google.workspace.meet.transcript.v2.fileGenerated",
]


class GoogleApps:
    """Wrapper for each endpoint that a multibillionaire company can't develop"""

    def __init__(self, id_token: str, refresh_token: Optional[str] = None):
        self._credentials = self._get_credentials(id_token, refresh_token)

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

    def get_user_info(self):
        service = build("oauth2", "v2", credentials=self._credentials)
        return service.userinfo().get().execute()

    def subscribe_meet_webhook(self, name: str, event_types: list[MeetEventType]):
        body = {
            "target_resource": f"//meet.googleapis.com/{name}",
            "event_types": event_types,
            "notification_endpoint": {
                "pubsub_topic": f"projects/{os.getenv('GOOGLE_PROJECT_ID')}/topics/{os.getenv('GOOGLE_WEBHOOK_TOPIC')}",
            },
            "payload_options": {},
        }
        service = build("workspaceevents", "v1", credentials=self._credentials)
        return service.subscriptions().create(body=body).execute()
