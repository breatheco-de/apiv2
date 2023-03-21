import random
from unittest.mock import MagicMock, call, patch
from ....permissions.contexts import academy
from ...mixins import AdmissionsTestCase

from breathecode.services import LaunchDarkly


def serializer(academy):
    return {
        'id': academy.id,
        'slug': academy.slug,
        'name': academy.name,
        'city': academy.city.name,
        'country': academy.country.name,
        'zip_code': academy.zip_code,
        'available_as_saas': academy.available_as_saas,
        'is_hidden_on_prework': academy.is_hidden_on_prework,
        'status': academy.status,
        'timezone': academy.timezone,
    }


value = random.randint(1, 1000)


class AcademyEventTestSuite(AdmissionsTestCase):

    @patch('ldclient.get', MagicMock())
    @patch('breathecode.services.launch_darkly.client.LaunchDarkly.context', MagicMock(return_value=value))
    def test_make_right_calls(self):
        model = self.bc.database.create(academy=1)

        ld = LaunchDarkly()
        result = academy(ld, model.academy)

        self.assertEqual(self.bc.database.list_of('admissions.Academy'), [
            self.bc.format.to_dict(model.academy),
        ])

        contexts = serializer(model.academy)

        self.assertEqual(LaunchDarkly.context.call_args_list, [
            call('academy-1', f'{model.academy.name} ({model.academy.slug})', 'academy-information',
                 contexts),
        ])

        self.assertEqual(result, value)
