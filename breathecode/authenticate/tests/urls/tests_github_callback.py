"""
Test cases for /user
"""

import re
import urllib
from unittest import mock

import capyc.pytest as capy
import pytest
from django.template import loader
from django.urls.base import reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient

import staging.pytest as staging
from breathecode.authenticate.tests.mocks.mocks import FakeResponse
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

from ..mocks import GithubRequestsMock


@pytest.fixture
def github_token(fake: capy.Fake):
    yield fake.slug()


@pytest.fixture(autouse=True)
def setup(
    db,
    monkeypatch: pytest.MonkeyPatch,
    http: staging.HTTP,
    github_user: dict,
    github_user_emails: list[str, dict],
    github_token: str,
):

    http.post(
        "https://github.com/login/oauth/access_token",
        data={
            "client_id": "123456",
            "client_secret": "123456",
            "redirect_uri": "https://breathecode.herokuapp.com/v1/auth/github/callback",
            "code": "Konan",
        },
        headers={"Accept": "application/json"},
        timeout=30,
    ).response(
        {"access_token": github_token, "scope": "repo,gist", "token_type": "bearer"},
        status=200,
    )

    http.get(
        "https://api.github.com/user",
        headers={"Authorization": f"token {github_token}"},
        timeout=30,
    ).response(
        github_user,
        status=200,
    )

    http.get(
        "https://api.github.com/user/emails",
        headers={"Authorization": f"token {github_token}"},
        timeout=30,
    ).response(
        github_user_emails,
        status=200,
    )

    routes = {
        "https://github.com/login/oauth/access_token": FakeResponse(
            status_code=200,
            data={"access_token": GithubRequestsMock.token, "scope": "repo,gist", "token_type": "bearer"},
        ),
        "https://rigobot.herokuapp.com/v1/auth/invite": FakeResponse(status_code=200, data={}),
    }

    def post_mock(url, *args, **kwargs):
        return routes.get(url, FakeResponse(status_code=404, data={"status": "fake request, not found"}))

    monkeypatch.setattr("requests.get", GithubRequestsMock.apply_get_requests_mock())
    monkeypatch.setattr("requests.post", post_mock)
    monkeypatch.setattr("django.db.models.signals.pre_delete.send_robust", mock.MagicMock(return_value=None))
    monkeypatch.setattr(
        "breathecode.admissions.signals.student_edu_status_updated.send_robust", mock.MagicMock(return_value=None)
    )

    monkeypatch.setenv("GITHUB_CLIENT_ID", "123456")
    monkeypatch.setenv("GITHUB_SECRET", "123456")
    monkeypatch.setenv("GITHUB_REDIRECT_URL", "https://breathecode.herokuapp.com/v1/auth/github/callback")
    monkeypatch.setattr("breathecode.authenticate.tasks.async_validate_email_invite", mock.MagicMock(return_value=None))

    yield


def render(message):
    request = None
    return loader.render_to_string(
        "message.html",
        {"MESSAGE": message, "BUTTON": None, "BUTTON_TARGET": "_blank", "LINK": None},
        request,
        using=None,
    )


@pytest.fixture
def github_user(fake: capy.Fake):
    return {
        "login": fake.user_name(),
        "id": 3018142,
        "node_id": fake.slug(),
        "avatar_url": fake.image_url(),
        "gravatar_id": "",
        "url": fake.url(),
        "html_url": fake.url(),
        "followers_url": fake.url(),
        "following_url": fake.url(),
        "gists_url": fake.url(),
        "starred_url": fake.url(),
        "subscriptions_url": fake.url(),
        "organizations_url": fake.url(),
        "repos_url": fake.url(),
        "events_url": fake.url(),
        "received_events_url": fake.url(),
        "type": "User",
        "user_view_type": "private",
        "site_admin": False,
        "name": None,
        "company": "@" + fake.user_name(),
        "blog": fake.url(),
        "location": None,
        "email": None,
        "hireable": None,
        "bio": fake.paragraph(),
        "twitter_username": "@" + fake.user_name(),
        "notification_email": None,
        "public_repos": 0,
        "public_gists": 0,
        "followers": 0,
        "following": 0,
        "created_at": "2024-12-18T22:50:38Z",
        "updated_at": "2024-12-18T22:50:41Z",
        "private_gists": 0,
        "total_private_repos": 0,
        "owned_private_repos": 0,
        "disk_usage": 0,
        "collaborators": 0,
        "two_factor_authentication": False,
        "plan": {"name": "free", "space": 123456789, "collaborators": 0, "private_repos": 123456789},
    }


def pick_github_data(data, fields=[], overwrite={}):
    result = {}

    for field in fields:
        result[overwrite.get(field, field)] = data[field]

    return result


@pytest.fixture
def github_user_emails(fake: capy.Fake):
    return [{"email": fake.email(), "primary": True, "verified": True, "visibility": "public"}]


def get_profile_fields(data={}):
    return {
        "id": 1,
        "user_id": 1,
        "avatar_url": "https://avatars2.githubusercontent.com/u/3018142?v=4",
        "bio": "I am an Computer engineer, Full-stack Developer\xa0and React Developer, I likes an API good, the clean code, the good programming practices",
        "phone": "",
        "show_tutorial": True,
        "twitter_username": None,
        "github_username": None,
        "portfolio_url": None,
        "linkedin_url": None,
        "blog": "https://www.facebook.com/chocoland.framework",
        **data,
    }


def get_credentials_github_fields(data={}):
    bio = (
        "I am an Computer engineer, Full-stack Developer\xa0and React "
        "Developer, I likes an API good, the clean code, the good programming "
        "practices"
    )
    return {
        "avatar_url": "https://avatars2.githubusercontent.com/u/3018142?v=4",
        "bio": bio,
        "blog": "https://www.facebook.com/chocoland.framework",
        "company": "@chocoland ",
        "email": "jdefreitaspinto@gmail.com",
        "github_id": 3018142,
        "name": "Jeferson De Freitas",
        "token": "e72e16c7e42f292c6912e7710c838347ae178b4a",
        "twitter_username": None,
        "user_id": 1,
        "username": "jefer94",
        **data,
    }


def test_github_callback__without_code(bc: Breathecode, client: APIClient):
    """Test /github/callback without auth"""
    url = reverse_lazy("authenticate:github_callback")
    params = {"url": "https://google.co.ve"}
    response = client.get(f"{url}?{urllib.parse.urlencode(params)}")

    data = response.json()
    expected = {"detail": "no-code", "status_code": 400}

    assert data == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert bc.database.list_of("auth.User") == []
    assert bc.database.list_of("authenticate.Profile") == []
    assert bc.database.list_of("authenticate.CredentialsGithub") == []
    assert bc.database.list_of("authenticate.ProfileAcademy") == []


def test_github_callback__user_not_exist(bc: Breathecode, client: APIClient):
    """Test /github/callback"""

    original_url_callback = "https://google.co.ve"
    code = "Konan"

    url = reverse_lazy("authenticate:github_callback")
    params = {"url": original_url_callback, "code": code}

    response = client.get(f"{url}?{urllib.parse.urlencode(params)}")
    content = bc.format.from_bytes(response.content)
    expected = render(
        "We could not find in our records the email associated to this github account, "
        'perhaps you want to signup to the platform first? <a href="'
        + original_url_callback
        + '">Back to 4Geeks.com</a>'
    )

    # dump error in external files
    if content != expected:
        with open("content.html", "w") as f:
            f.write(content)

        with open("expected.html", "w") as f:
            f.write(expected)

    assert content == expected
    assert response.status_code == status.HTTP_200_OK

    assert bc.database.list_of("auth.User") == []
    assert bc.database.list_of("authenticate.Profile") == []
    assert bc.database.list_of("authenticate.CredentialsGithub") == []
    assert bc.database.list_of("authenticate.ProfileAcademy") == []


def test_github_callback__user_not_exist_but_waiting_list(
    bc: Breathecode, client: APIClient, github_user_emails: list[str, dict]
):
    """Test /github/callback"""

    user_invite = {"status": "WAITING_LIST", "email": github_user_emails[0]["email"]}
    bc.database.create(user_invite=user_invite)

    original_url_callback = "https://google.co.ve"
    code = "Konan"

    url = reverse_lazy("authenticate:github_callback")
    params = {"url": original_url_callback, "code": code}

    response = client.get(f"{url}?{urllib.parse.urlencode(params)}")
    content = bc.format.from_bytes(response.content)
    expected = render(
        "You are still number 1 on the waiting list, we will email you once you are given access "
        f'<a href="{original_url_callback}">Back to 4Geeks.com</a>'
    )

    # dump error in external files
    if content != expected:
        with open("content.html", "w") as f:
            f.write(content)

        with open("expected.html", "w") as f:
            f.write(expected)

    assert content == expected
    assert response.status_code == status.HTTP_200_OK

    assert bc.database.list_of("auth.User") == []
    assert bc.database.list_of("authenticate.Profile") == []
    assert bc.database.list_of("authenticate.CredentialsGithub") == []
    assert bc.database.list_of("authenticate.ProfileAcademy") == []


def test_github_callback__with_user(bc: Breathecode, client: APIClient, github_token: str):
    """Test /github/callback"""
    user_kwargs = {"email": "JDEFREITASPINTO@GMAIL.COM"}
    role_kwargs = {"slug": "student", "name": "Student"}
    model = bc.database.create(role=True, user=True, user_kwargs=user_kwargs, role_kwargs=role_kwargs)

    original_url_callback = "https://google.co.ve"
    token_pattern = re.compile("^" + original_url_callback.replace(".", r"\.") + r"\?token=[0-9a-zA-Z]{,40}$")
    code = "Konan"

    url = reverse_lazy("authenticate:github_callback")
    params = {"url": original_url_callback, "code": code}
    response = client.get(f"{url}?{urllib.parse.urlencode(params)}")

    assert response.status_code == status.HTTP_302_FOUND
    assert bool(token_pattern.match(response.url)) == True

    assert bc.database.list_of("auth.User") == [{**bc.format.to_dict(model.user)}]

    assert bc.database.list_of("authenticate.Profile") == []
    assert bc.database.list_of("authenticate.CredentialsGithub") == [
        get_credentials_github_fields(
            data={
                "token": github_token,
            }
        ),
    ]
    assert bc.database.list_of("authenticate.ProfileAcademy") == [
        bc.format.to_dict(model.profile_academy),
    ]


def test_github_callback__with_user__with_email_in_uppercase(
    bc: Breathecode, client: APIClient, github_user: dict, github_token: str, github_user_emails: list[str, dict]
):
    """Test /github/callback"""
    user_kwargs = {"email": github_user_emails[0]["email"].upper()}
    role_kwargs = {"slug": "student", "name": "Student"}
    model = bc.database.create(role=True, user=True, user_kwargs=user_kwargs, role_kwargs=role_kwargs)

    original_url_callback = "https://google.co.ve"
    token_pattern = re.compile("^" + original_url_callback.replace(".", r"\.") + r"\?token=[0-9a-zA-Z]{,40}$")
    code = "Konan"

    url = reverse_lazy("authenticate:github_callback")
    params = {"url": original_url_callback, "code": code}
    response = client.get(f"{url}?{urllib.parse.urlencode(params)}")

    with open("content.html", "w") as f:
        f.write(bc.format.from_bytes(response.content))

    assert response.status_code == status.HTTP_302_FOUND
    assert bool(token_pattern.match(response.url)) == True

    assert bc.database.list_of("auth.User") == [{**bc.format.to_dict(model.user)}]

    assert bc.database.list_of("authenticate.Profile") == [
        get_profile_fields(
            data={
                **pick_github_data(github_user, fields=["blog", "bio", "avatar_url", "twitter_username"]),
            }
        ),
    ]
    assert bc.database.list_of("authenticate.CredentialsGithub") == [
        get_credentials_github_fields(
            data={
                "token": github_token,
                **pick_github_data(
                    github_user,
                    fields=["blog", "bio", "avatar_url", "twitter_username", "login", "company", "name", "email"],
                    overwrite={"login": "username"},
                ),
            }
        ),
    ]
    assert bc.database.list_of("authenticate.ProfileAcademy") == []


def test_github_callback__with_bad_user_in_querystring(
    bc: Breathecode, client: APIClient, github_user_emails: list[str, dict]
):
    """Test /github/callback"""
    user_kwargs = {"email": github_user_emails[0]["email"].upper()}
    role_kwargs = {"slug": "student", "name": "Student"}
    model = bc.database.create(
        role=True, user=True, profile_academy=True, user_kwargs=user_kwargs, role_kwargs=role_kwargs, token=True
    )

    original_url_callback = "https://google.co.ve"
    code = "Konan"

    url = reverse_lazy("authenticate:github_callback")
    params = {"url": original_url_callback, "code": code, "user": "b14f"}
    response = client.get(f"{url}?{urllib.parse.urlencode(params)}")
    json = response.json()
    expected = {"detail": "token-not-found", "status_code": 404}

    assert json == expected
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert bc.database.list_of("auth.User") == [{**bc.format.to_dict(model.user)}]
    assert bc.database.list_of("authenticate.Profile") == []
    assert bc.database.list_of("authenticate.CredentialsGithub") == []
    assert bc.database.list_of("authenticate.ProfileAcademy") == [
        bc.format.to_dict(model.profile_academy),
    ]


def test_github_callback__with_user(
    bc: Breathecode,
    client: APIClient,
    github_user: dict,
    github_token: str,
):
    """Test /github/callback"""
    user_kwargs = {"email": "JDEFREITASPINTO@GMAIL.COM"}
    role_kwargs = {"slug": "student", "name": "Student"}
    model = bc.database.create(
        role=True, user=True, profile_academy=True, user_kwargs=user_kwargs, role_kwargs=role_kwargs, token=True
    )

    original_url_callback = "https://google.co.ve"
    token_pattern = re.compile("^" + original_url_callback.replace(".", r"\.") + r"\?token=[0-9a-zA-Z]{,40}$")
    code = "Konan"

    token = model.token

    url = reverse_lazy("authenticate:github_callback")
    params = {"url": original_url_callback, "code": code, "user": token}
    response = client.get(f"{url}?{urllib.parse.urlencode(params)}")

    assert response.status_code == status.HTTP_302_FOUND
    assert bool(token_pattern.match(response.url)) == True

    assert bc.database.list_of("auth.User") == [{**bc.format.to_dict(model.user)}]

    assert bc.database.list_of("authenticate.Profile") == [
        get_profile_fields(
            data={
                **pick_github_data(github_user, fields=["blog", "bio", "avatar_url", "twitter_username"]),
            }
        ),
    ]
    assert bc.database.list_of("authenticate.CredentialsGithub") == [
        get_credentials_github_fields(
            data={
                "token": github_token,
                **pick_github_data(
                    github_user,
                    fields=["blog", "bio", "avatar_url", "twitter_username", "login", "company", "name", "email"],
                    overwrite={"login": "username"},
                ),
            }
        ),
    ]
    assert bc.database.list_of("authenticate.ProfileAcademy") == [
        bc.format.to_dict(model.profile_academy),
    ]


def test_github_callback__with_user__profile_without_avatar_url(
    bc: Breathecode,
    client: APIClient,
    github_user: dict,
    github_token: str,
):
    """Test /github/callback"""
    user_kwargs = {"email": "JDEFREITASPINTO@GMAIL.COM"}
    role_kwargs = {"slug": "student", "name": "Student"}
    model = bc.database.create(
        role=True,
        user=True,
        profile_academy=True,
        user_kwargs=user_kwargs,
        role_kwargs=role_kwargs,
        profile=1,
        token=True,
    )

    original_url_callback = "https://google.co.ve"
    token_pattern = re.compile("^" + original_url_callback.replace(".", r"\.") + r"\?token=[0-9a-zA-Z]{,40}$")
    code = "Konan"

    token = model.token

    url = reverse_lazy("authenticate:github_callback")
    params = {"url": original_url_callback, "code": code, "user": token}
    response = client.get(f"{url}?{urllib.parse.urlencode(params)}")

    assert response.status_code == status.HTTP_302_FOUND
    assert bool(token_pattern.match(response.url)) == True

    assert bc.database.list_of("auth.User") == [{**bc.format.to_dict(model.user)}]

    assert bc.database.list_of("authenticate.Profile") == [
        get_profile_fields(
            data={
                "bio": None,
                "blog": None,
                **pick_github_data(github_user, fields=["avatar_url"]),
            }
        ),
    ]
    assert bc.database.list_of("authenticate.CredentialsGithub") == [
        get_credentials_github_fields(
            data={
                "token": github_token,
                **pick_github_data(
                    github_user,
                    fields=["blog", "bio", "avatar_url", "twitter_username", "login", "company", "name", "email"],
                    overwrite={"login": "username"},
                ),
            }
        ),
    ]
    assert bc.database.list_of("authenticate.ProfileAcademy") == [
        bc.format.to_dict(model.profile_academy),
    ]


def test_github_callback__with_user__profile_with_avatar_url(
    bc: Breathecode,
    client: APIClient,
    github_user: dict,
    github_token: str,
):
    """Test /github/callback"""
    user_kwargs = {"email": "JDEFREITASPINTO@GMAIL.COM"}
    role_kwargs = {"slug": "student", "name": "Student"}
    profile = {"avatar_url": bc.fake.url()}
    model = bc.database.create(
        role=True,
        user=True,
        profile_academy=True,
        user_kwargs=user_kwargs,
        role_kwargs=role_kwargs,
        profile=profile,
        token=True,
    )

    original_url_callback = "https://google.co.ve"
    token_pattern = re.compile("^" + original_url_callback.replace(".", r"\.") + r"\?token=[0-9a-zA-Z]{,40}$")
    code = "Konan"

    token = model.token

    url = reverse_lazy("authenticate:github_callback")
    params = {"url": original_url_callback, "code": code, "user": token}
    response = client.get(f"{url}?{urllib.parse.urlencode(params)}")

    assert response.status_code == status.HTTP_302_FOUND
    assert bool(token_pattern.match(response.url)) == True

    assert bc.database.list_of("auth.User") == [{**bc.format.to_dict(model.user)}]

    assert bc.database.list_of("authenticate.Profile") == [
        get_profile_fields(
            data={
                "bio": None,
                "blog": None,
                **profile,
            }
        ),
    ]
    assert bc.database.list_of("authenticate.CredentialsGithub") == [
        get_credentials_github_fields(
            data={
                "token": github_token,
                **pick_github_data(
                    github_user,
                    fields=["blog", "bio", "avatar_url", "twitter_username", "login", "company", "name", "email"],
                    overwrite={"login": "username"},
                ),
            }
        ),
    ]
    assert bc.database.list_of("authenticate.ProfileAcademy") == [
        bc.format.to_dict(model.profile_academy),
    ]


def test_github_callback__with_user_different_email__without_credetials_of_github__without_cohort_user(
    bc: Breathecode,
    client: APIClient,
    github_user: dict,
    github_token: str,
):
    """Test /github/callback"""
    user = {"email": "FJOSE123@GMAIL.COM"}
    role = {"slug": "student", "name": "Student"}
    model = bc.database.create(role=role, user=user, profile_academy=True, token=True)

    original_url_callback = "https://google.co.ve"
    token_pattern = re.compile("^" + original_url_callback.replace(".", r"\.") + r"\?token=[0-9a-zA-Z]{,40}$")
    code = "Konan"

    token = model.token

    url = reverse_lazy("authenticate:github_callback")
    params = {"url": original_url_callback, "code": code, "user": token}
    response = client.get(f"{url}?{urllib.parse.urlencode(params)}")

    assert response.status_code == status.HTTP_302_FOUND
    assert bool(token_pattern.match(response.url)) == True

    assert bc.database.list_of("auth.User") == [{**bc.format.to_dict(model.user)}]

    assert bc.database.list_of("authenticate.Profile") == [
        get_profile_fields(
            data={
                **pick_github_data(github_user, fields=["blog", "bio", "avatar_url", "twitter_username"]),
            }
        ),
    ]
    assert bc.database.list_of("authenticate.CredentialsGithub") == [
        get_credentials_github_fields(
            data={
                "token": github_token,
                **pick_github_data(
                    github_user,
                    fields=["blog", "bio", "avatar_url", "twitter_username", "login", "company", "name", "email"],
                    overwrite={"login": "username"},
                ),
            }
        ),
    ]
    assert bc.database.list_of("authenticate.ProfileAcademy") == [
        bc.format.to_dict(model.profile_academy),
    ]


def test_github_callback__with_user_different_email__without_credetials_of_github__with_cohort_user(
    bc: Breathecode,
    client: APIClient,
    github_user: dict,
    github_token: str,
):
    """Test /github/callback"""
    user = {"email": "FJOSE123@GMAIL.COM"}
    role = {"slug": "student", "name": "Student"}
    model = bc.database.create(role=role, user=user, profile_academy=True, cohort_user=1, token=True)

    original_url_callback = "https://google.co.ve"
    token_pattern = re.compile("^" + original_url_callback.replace(".", r"\.") + r"\?token=[0-9a-zA-Z]{,40}$")
    code = "Konan"

    token = model.token

    url = reverse_lazy("authenticate:github_callback")
    params = {"url": original_url_callback, "code": code, "user": token}
    response = client.get(f"{url}?{urllib.parse.urlencode(params)}")

    assert response.status_code == status.HTTP_302_FOUND
    assert bool(token_pattern.match(response.url)) == True

    assert bc.database.list_of("auth.User") == [{**bc.format.to_dict(model.user)}]

    assert bc.database.list_of("authenticate.Profile") == [
        get_profile_fields(
            data={
                **pick_github_data(github_user, fields=["blog", "bio", "avatar_url", "twitter_username"]),
            }
        ),
    ]
    assert bc.database.list_of("authenticate.CredentialsGithub") == [
        get_credentials_github_fields(
            data={
                "token": github_token,
                **pick_github_data(
                    github_user,
                    fields=["blog", "bio", "avatar_url", "twitter_username", "login", "company", "name", "email"],
                    overwrite={"login": "username"},
                ),
            }
        ),
    ]
    assert bc.database.list_of("authenticate.ProfileAcademy") == [
        bc.format.to_dict(model.profile_academy),
    ]


def test_github_callback__with_user_different_email__with_credentials_of_github__without_cohort_user(
    bc: Breathecode,
    client: APIClient,
    github_user: dict,
    github_token: str,
):
    """Test /github/callback"""
    users = [{"email": "FJOSE123@GMAIL.COM"}, {"email": "jdefreitaspinto@gmail.com"}]
    role = {"slug": "student", "name": "Student"}
    credentials_github = {"github_id": 3018142}
    token = {"user_id": 2}
    model = bc.database.create(
        role=role, user=users, profile_academy=True, credentials_github=credentials_github, token=token
    )

    original_url_callback = "https://google.co.ve"
    token_pattern = re.compile("^" + original_url_callback.replace(".", r"\.") + r"\?token=[0-9a-zA-Z]{,40}$")
    code = "Konan"

    token = model.token

    url = reverse_lazy("authenticate:github_callback")
    params = {"url": original_url_callback, "code": code, "user": token}
    response = client.get(f"{url}?{urllib.parse.urlencode(params)}")

    assert response.status_code == status.HTTP_302_FOUND
    assert bool(token_pattern.match(response.url)) == True

    assert bc.database.list_of("auth.User") == bc.format.to_dict(model.user)

    assert bc.database.list_of("authenticate.Profile") == [
        get_profile_fields(
            data={
                "user_id": 2,
                **pick_github_data(github_user, fields=["blog", "bio", "avatar_url", "twitter_username"]),
            }
        ),
    ]
    assert bc.database.list_of("authenticate.CredentialsGithub") == [
        get_credentials_github_fields(
            data={
                "user_id": 2,
                "token": github_token,
                **pick_github_data(
                    github_user,
                    fields=["blog", "bio", "avatar_url", "twitter_username", "login", "company", "name", "email"],
                    overwrite={"login": "username"},
                ),
            }
        ),
    ]
    assert bc.database.list_of("authenticate.ProfileAcademy") == [
        bc.format.to_dict(model.profile_academy),
    ]


def test_github_callback__with_user_different_email__with_credentials_of_github__with_cohort_user(
    bc: Breathecode,
    client: APIClient,
    http: staging.HTTP,
    github_user: dict,
    github_token: str,
):

    users = [{"email": "FJOSE123@GMAIL.COM"}, {"email": "jdefreitaspinto@gmail.com"}]
    role = {"slug": "student", "name": "Student"}
    credentials_github = {"github_id": 3018142}
    token = {"user_id": 2}
    cohort_user = {"user_id": 2}
    model = bc.database.create(
        role=role,
        user=users,
        cohort_user=cohort_user,
        profile_academy=True,
        credentials_github=credentials_github,
        token=token,
    )

    http.post(
        "https://rigobot.herokuapp.com/v1/auth/invite",
        data={"organization": "4geeks", "user_token": model.token.key},
        headers={"Accept": "application/json"},
        timeout=30,
    ).response(
        {},
        status=200,
    )

    original_url_callback = "https://google.co.ve"
    token_pattern = re.compile("^" + original_url_callback.replace(".", r"\.") + r"\?token=[0-9a-zA-Z]{,40}$")
    code = "Konan"

    token = model.token

    url = reverse_lazy("authenticate:github_callback")
    params = {"url": original_url_callback, "code": code, "user": token}
    response = client.get(f"{url}?{urllib.parse.urlencode(params)}")

    assert response.status_code == status.HTTP_302_FOUND
    assert bool(token_pattern.match(response.url)) == True

    assert bc.database.list_of("auth.User") == bc.format.to_dict(model.user)

    assert bc.database.list_of("authenticate.Profile") == [
        get_profile_fields(
            data={
                "user_id": 2,
                **pick_github_data(github_user, fields=["blog", "bio", "avatar_url", "twitter_username"]),
            }
        ),
    ]
    assert bc.database.list_of("authenticate.CredentialsGithub") == [
        get_credentials_github_fields(
            data={
                "user_id": 2,
                "token": github_token,
                **pick_github_data(
                    github_user,
                    fields=["blog", "bio", "avatar_url", "twitter_username", "login", "company", "name", "email"],
                    overwrite={"login": "username"},
                ),
            }
        ),
    ]

    assert bc.database.list_of("authenticate.ProfileAcademy") == [
        bc.format.to_dict(model.profile_academy),
        {
            "academy_id": 1,
            "address": None,
            "email": "jdefreitaspinto@gmail.com",
            "first_name": model.user[1].first_name,
            "id": 2,
            "last_name": model.user[1].last_name,
            "phone": "",
            "role_id": "student",
            "status": "ACTIVE",
            "user_id": 2,
        },
    ]
