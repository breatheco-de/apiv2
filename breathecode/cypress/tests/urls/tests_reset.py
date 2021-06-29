import os
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from rest_framework import status

from ..mixins import CypressTestCase


def os_system_mock():
    def system(command: str):
        pass

    return MagicMock(side_effect=system)


class AcademyEventTestSuite(CypressTestCase):
    def test_reset__bad_environment__not_exits(self):
        if 'ALLOW_UNSAFE_CYPRESS_APP' in os.environ:
            del os.environ['ALLOW_UNSAFE_CYPRESS_APP']

        url = reverse_lazy('cypress:reset')
        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'is-not-allowed', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset__bad_environment__empty_string(self):
        os.environ['ALLOW_UNSAFE_CYPRESS_APP'] = ''

        url = reverse_lazy('cypress:reset')
        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'is-not-allowed', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch.object(os, 'system', new=os_system_mock())
    def test_reset(self):
        import os
        mock = os.system

        os.environ['ALLOW_UNSAFE_CYPRESS_APP'] = 'True'
        url = reverse_lazy('cypress:reset')
        self.generate_models(academy=True, form_entry=True)

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.all_academy_dict(), [])
        self.assertEqual(self.all_form_entry_dict(), [])
        self.assertEqual(mock.call_args_list, [
            call('python manage.py loaddata breathecode/admissions/fixtures/'
                 'dev_data.json'),
            call('python manage.py loaddata breathecode/authenticate/fixtures/'
                 'dev_data.json'),
            call('python manage.py loaddata breathecode/authenticate/fixtures/'
                 'dev_users.json'),
            call('python manage.py loaddata breathecode/marketing/fixtures/'
                 'dev_data.json'),
        ])
