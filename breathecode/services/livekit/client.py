import base64
import os
from typing import Any, Dict, Optional

import requests

__all__ = ["LiveKitAdmin"]


class LiveKitAdmin:
    def __init__(
        self,
        http_url: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        timeout: int = 10,
    ) -> None:
        self.http_url = (http_url or os.getenv("LIVEKIT_HTTP_URL") or "").rstrip("/")
        self.api_key = api_key or os.getenv("LIVEKIT_API_KEY") or ""
        self.api_secret = api_secret or os.getenv("LIVEKIT_API_SECRET") or ""
        self.timeout = timeout

        if not self.http_url:
            raise Exception("LIVEKIT_HTTP_URL is not configured")
        if not self.api_key or not self.api_secret:
            raise Exception("LIVEKIT_API_KEY/LIVEKIT_API_SECRET are not configured")

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
