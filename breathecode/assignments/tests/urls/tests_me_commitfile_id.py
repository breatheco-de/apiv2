"""
Test /answer
"""

import json
import random
from unittest.mock import MagicMock, call, patch

import pytest
import requests
from django.urls.base import reverse_lazy
from linked_services.django.actions import reset_app_cache
from rest_framework import status

from ..mixins import AssignmentsTestCase


@pytest.fixture(autouse=True)
def setup(db):
    reset_app_cache()
    yield


class MediaTestSuite(AssignmentsTestCase):

    # When: no auth
    # Then: response 401
    def test_no_auth(self):
        url = reverse_lazy("assignments:me_commitfile_id", kwargs={"commitfile_id": 1})
        response = self.client.get(url)

        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.bc.database.list_of("assignments.Task"), [])

    # When: auth in get
    # Then: response 200
    def test__get__auth(self):
        expected = {"data": {"getTask": {"id": random.randint(1, 100)}}}
        query = {
            self.bc.fake.slug(): self.bc.fake.slug(),
            self.bc.fake.slug(): self.bc.fake.slug(),
            self.bc.fake.slug(): self.bc.fake.slug(),
        }

        mock = MagicMock()
        mock.raw = iter([json.dumps(expected).encode()])
        mock.headers = {"Content-Type": "application/json"}
        code = random.randint(200, 299)
        mock.status_code = code
        mock.reason = "OK"

        task = {"github_url": self.bc.fake.url()}
        model = self.bc.database.create(profile_academy=1, task=task, app={"slug": "rigobot"})
        self.client.force_authenticate(model.user)

        url = (
            reverse_lazy("assignments:me_commitfile_id", kwargs={"commitfile_id": 1})
            + "?"
            + self.bc.format.querystring(query)
        )

        token = self.bc.random.string(lower=True, upper=True, symbol=True, number=True, size=20)
        with patch("linked_services.django.actions.get_jwt", MagicMock(return_value=token)):
            with patch.multiple("requests", get=MagicMock(return_value=mock)):
                response = self.client.get(url)
                self.bc.check.calls(
                    requests.get.call_args_list,
                    [
                        call(
                            model.app.app_url + "/v1/finetuning/commitfile/1",
                            params=query,
                            stream=True,
                            headers={"Authorization": f"Link App=breathecode,Token={token}"},
                        ),
                    ],
                )

        self.assertEqual(response.getvalue().decode("utf-8"), json.dumps(expected))
        self.assertEqual(response.status_code, code)
        self.assertEqual(self.bc.database.list_of("assignments.Task"), [self.bc.format.to_dict(model.task)])
