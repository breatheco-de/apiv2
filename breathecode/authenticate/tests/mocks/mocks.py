"""
Collections of mocks used to login in authorize microservice
"""

from unittest.mock import Mock


class GoogleCloudStorageMock:

    @staticmethod
    def get_bucket_object():

        def side_effect():
            return None

        return Mock(side_effect=side_effect)


class FakeResponse:
    """Simutate Response to be used by mocks"""

    status_code = 200
    data = {}

    def __init__(self, status_code, data):
        self.data = data
        self.status_code = status_code

    def json(self):
        """Convert Response to JSON"""
        return self.data


def requests_mock(routes: dict, method="get"):
    """Arequests mock"""
    if method == "get":

        def side_effect(url, headers=None):
            return routes.get(url, f"unhandled request {url}")

    elif method == "post":

        def side_effect(url, data=None, headers=None):
            return routes.get(url, f"unhandled request {url}")

    else:
        raise Exception(f"{method} are not implemented too")
    return Mock(side_effect=side_effect)


class GithubRequestsMock:
    """Github requests mock"""

    token = "e72e16c7e42f292c6912e7710c838347ae178b4a"

    @staticmethod
    def user():
        """Static https://api.github.com/user"""
        return FakeResponse(
            status_code=200,
            data={
                "login": "jefer94",
                "id": 3018142,
                "node_id": "MDQ6VXNlcjMwMTgxNDI=",
                "avatar_url": "https://avatars2.githubusercontent.com/u/3018142?v=4",
                "gravatar_id": "",
                "url": "https://api.github.com/users/jefer94",
                "html_url": "https://github.com/jefer94",
                "followers_url": "https://api.github.com/users/jefer94/followers",
                "following_url": "https://api.github.com/users/jefer94/following{/other_user}",
                "gists_url": "https://api.github.com/users/jefer94/gists{/gist_id}",
                "starred_url": "https://api.github.com/users/jefer94/starred{/owner}{/repo}",
                "subscriptions_url": "https://api.github.com/users/jefer94/subscriptions",
                "organizations_url": "https://api.github.com/users/jefer94/orgs",
                "repos_url": "https://api.github.com/users/jefer94/repos",
                "events_url": "https://api.github.com/users/jefer94/events{/privacy}",
                "received_events_url": "https://api.github.com/users/jefer94/received_events",
                "type": "User",
                "site_admin": False,
                "name": "Jeferson De Freitas",
                "company": "@chocoland ",
                "blog": "https://www.facebook.com/chocoland.framework",
                "location": "Colombia, Magdalena, Santa Marta, Gaira",
                "email": "jdefreitaspinto@gmail.com",
                "hireable": True,
                "bio": "I am an Computer engineer, Full-stack Developer and React Developer, I likes"
                + " an API good, the clean code, the good programming practices",
                "twitter_username": None,
                "public_repos": 70,
                "public_gists": 1,
                "followers": 9,
                "following": 5,
                "created_at": "2012-12-11T17:00:30Z",
                "updated_at": "2020-10-29T19:15:13Z",
                "private_gists": 0,
                "total_private_repos": 2,
                "owned_private_repos": 1,
                "disk_usage": 211803,
                "collaborators": 0,
                "two_factor_authentication": False,
                "plan": {"name": "free", "space": 976562499, "collaborators": 0, "private_repos": 10000},
            },
        )

    @staticmethod
    def user_emails():
        """Static https://api.github.com/user/emails"""
        return FakeResponse(
            status_code=200,
            data=[
                {"email": "jeferson-94@hotmail.com", "primary": False, "verified": True, "visibility": None},
                {"email": "jdefreitaspinto@gmail.com", "primary": True, "verified": True, "visibility": "public"},
            ],
        )

    @staticmethod
    def access_token():
        """Static https://github.com/login/oauth/access_token"""
        return FakeResponse(
            status_code=200,
            data={"access_token": GithubRequestsMock.token, "scope": "repo,gist", "token_type": "bearer"},
        )

    @staticmethod
    def apply_get_requests_mock():
        """Apply get requests mock"""
        routes = {
            "https://api.github.com/user": GithubRequestsMock.user(),
            "https://api.github.com/user/emails": GithubRequestsMock.user_emails(),
        }
        return requests_mock(routes)

    @staticmethod
    def apply_post_requests_mock():
        """Apply post requests mock"""
        routes = {"https://github.com/login/oauth/access_token": GithubRequestsMock.access_token()}
        return requests_mock(routes, method="post")


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
