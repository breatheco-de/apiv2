"""
Collections of mocks used to login in authorize microservice
"""

from .fake_response import FakeResponse
from .requests_mock import requests_mock


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
