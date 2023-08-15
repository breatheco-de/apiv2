"""
Test /answer
"""
import json
import random
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.utils.service import Service

from ..mixins import AssignmentsTestCase


class MediaTestSuite(AssignmentsTestCase):

    # When: no auth
    # Then: response 401
    def test_no_auth(self):
        url = reverse_lazy('assignments:academy_coderevision')
        response = self.client.get(url)

        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])

    # When: no capability
    # Then: response 403
    def test_no_capability(self):
        model = self.bc.database.create(user=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:academy_coderevision')
        response = self.client.get(url)

        json = response.json()
        expected = {
            'detail': 'You (user: 1) don\'t have this capability: read_assignment for academy 1',
            'status_code': 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])

    # When: auth
    # Then: response 200
    def test_auth(self):
        self.bc.request.set_headers(academy=1)

        expected = {'data': {'getTask': {'id': random.randint(1, 100)}}}
        query = {
            self.bc.fake.slug(): self.bc.fake.slug(),
            self.bc.fake.slug(): self.bc.fake.slug(),
            self.bc.fake.slug(): self.bc.fake.slug(),
        }

        mock = MagicMock()
        mock.raw = iter([json.dumps(expected).encode()])
        mock.headers = {'Content-Type': 'application/json'}
        code = random.randint(200, 299)
        mock.status_code = code
        mock.reason = 'OK'

        task = {'github_url': self.bc.fake.url()}
        model = self.bc.database.create(profile_academy=1, task=task, role=1, capability='read_assignment')
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('assignments:academy_task_id_coderevision',
                           kwargs={'task_id': 1}) + '?' + self.bc.format.querystring(query)

        with patch.multiple('breathecode.utils.service.Service',
                            __init__=MagicMock(return_value=None),
                            get=MagicMock(return_value=mock)):
            response = self.client.get(url)
            self.bc.check.calls(Service.get.call_args_list, [
                call('/v1/finetuning/coderevision',
                     params={
                         **query,
                         'repo': model.task.github_url,
                     },
                     stream=True),
            ])

        self.assertEqual(response.getvalue().decode('utf-8'), json.dumps(expected))
        self.assertEqual(response.status_code, code)
        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])
