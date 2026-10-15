"""
Test /v1/auth/logout/
"""

import capyc.pytest as capy
import pytest
from django.urls.base import reverse_lazy
from rest_framework import status


@pytest.fixture(autouse=True)
def setup(db):
    yield


def remaining_token_keys(database: capy.Database) -> list[str]:
    return sorted(token["key"] for token in database.list_of("authenticate.Token"))


@pytest.mark.parametrize("method", ["get", "post"])
def test_without_auth(database: capy.Database, client: capy.Client, method: str):
    url = reverse_lazy("authenticate:logout")
    database.create(user=1)

    response = getattr(client, method)(url, format="json")
    json = response.json()

    assert json == {"detail": "Authentication credentials were not provided.", "status_code": 401}
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize("method", ["get", "post"])
def test_only_deletes_tokens_of_the_requesting_user(database: capy.Database, client: capy.Client, method: str):
    url = reverse_lazy("authenticate:logout")
    database.create(
        user=2,
        token=[
            {"key": "user1-login-a", "token_type": "login", "user_id": 1},
            {"key": "user1-login-b", "token_type": "login", "user_id": 1},
            {"key": "user1-permanent", "token_type": "permanent", "user_id": 1},
            {"key": "user2-login", "token_type": "login", "user_id": 2},
            {"key": "user2-permanent", "token_type": "permanent", "user_id": 2},
        ],
    )

    response = getattr(client, method)(url, format="json", HTTP_AUTHORIZATION="Token user1-login-a")
    json = response.json()

    assert json == {"message": "User tokens successfully deleted"}
    assert response.status_code == status.HTTP_200_OK
    assert remaining_token_keys(database) == ["user1-permanent", "user2-login", "user2-permanent"]


def test_deletes_the_non_login_token_used_to_authenticate(database: capy.Database, client: capy.Client):
    url = reverse_lazy("authenticate:logout")
    database.create(
        user=2,
        token=[
            {"key": "user1-login", "token_type": "login", "user_id": 1},
            {"key": "user1-permanent", "token_type": "permanent", "user_id": 1},
            {"key": "user2-login", "token_type": "login", "user_id": 2},
        ],
    )

    response = client.post(url, format="json", HTTP_AUTHORIZATION="Token user1-permanent")
    json = response.json()

    assert json == {"message": "User tokens successfully deleted"}
    assert response.status_code == status.HTTP_200_OK
    assert remaining_token_keys(database) == ["user2-login"]
