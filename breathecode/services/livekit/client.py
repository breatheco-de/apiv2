import base64
import os
from typing import Any, Dict, Optional

import requests

from breathecode.events.models import AcademyEventSettings

__all__ = ["LiveKitAdmin"]


class LiveKitAdmin:
    def __init__(
        self,
        http_url: Optional[str] = None,
        server_url: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        timeout: int = 10,
        academy=None,
    ) -> None:

        if academy and not http_url and not api_key and not api_secret and not server_url:
            academy_settings = AcademyEventSettings.objects.filter(academy=academy).first()
            if academy_settings:
                http_url = academy_settings.livekit_http_url
                api_key = academy_settings.livekit_api_key
                api_secret = academy_settings.livekit_api_secret
                server_url = academy_settings.livekit_url

        self.http_url = (http_url.rstrip("/") if http_url else "") or os.getenv("LIVEKIT_HTTP_URL") or ""
        self.api_key = api_key or os.getenv("LIVEKIT_API_KEY") or ""
        self.api_secret = api_secret or os.getenv("LIVEKIT_API_SECRET") or ""
        self.server_url = server_url or os.getenv("LIVEKIT_URL") or ""
        self.timeout = timeout

        if not self.http_url:
            raise Exception("LIVEKIT_HTTP_URL is not configured")
        if not self.api_key or not self.api_secret:
            raise Exception("LIVEKIT_API_KEY/LIVEKIT_API_SECRET are not configured")

    def get_api_key(self):
        return self.api_key

    def get_api_secret(self):
        return self.api_secret

    def get_http_url(self):
        return self.http_url

    def get_server_url(self):
        return self.server_url

    def _auth_headers(self) -> Dict[str, str]:
        token = base64.b64encode(f"{self.api_key}:{self.api_secret}".encode()).decode()
        return {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
        }

    def create_room(self, name: str, empty_timeout: int = 900, max_participants: int = 300) -> Dict[str, Any]:
        """Create a room using LiveKit RoomService (Twirp over HTTP).

        Notes:
        - Idempotent in practice: if the room exists, LiveKit may return an error; callers may swallow it.
        - We prefer pre-creating to attach limits like max_participants.
        """

        url = f"{self.http_url}/twirp/livekit.RoomService/CreateRoom"
        payload = {
            "name": name,
            "empty_timeout": empty_timeout,
            "max_participants": max_participants,
        }
        resp = requests.post(url, json=payload, headers=self._auth_headers(), timeout=self.timeout)
        # If room already exists, some deployments return code != 200; let callers decide how to handle
        if resp.status_code >= 200 and resp.status_code < 300:
            return resp.json()
        # Raise for visibility; the caller may catch and ignore for idempotency
        resp.raise_for_status()
        return resp.json()
