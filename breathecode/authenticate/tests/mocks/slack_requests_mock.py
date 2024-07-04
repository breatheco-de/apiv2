"""
Collections of mocks used to login in authorize microservice
"""

from .fake_response import FakeResponse
from .requests_mock import requests_mock


class SlackRequestsMock:
    """Github requests mock"""

    token = "e72e16c7e42f292c6912e7710c838347ae178b4a"

    @staticmethod
    def access():
        """Static https://slack.com/api/oauth.v2.access"""
        return FakeResponse(
            status_code=200,
            data={
                "ok": True,
                "access_token": "xoxb-17653672481-19874698323-pdFZKVeTuE8sk7oOcBrzbqgy",
                "token_type": "bot",
                "scope": "commands,incoming-webhook",
                "bot_user_id": "U0KRQLJ9H",
                "app_id": "A0KRD7HC3",
                "team": {"name": "Slack Softball Team", "id": "T9TK3CUKW"},
                "enterprise": {"name": "slack-sports", "id": "E12345678"},
                "authed_user": {
                    "id": "U1234",
                    "scope": "chat:write",
                    "access_token": "xoxp-1234",
                    "token_type": "user",
                },
            },
        )

    @staticmethod
    def apply_post_requests_mock():
        """Apply get requests mock"""
        routes = {"https://slack.com/api/oauth.v2.access": SlackRequestsMock.access()}
        return requests_mock(routes, method="post")
