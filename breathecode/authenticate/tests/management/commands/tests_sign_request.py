"""
Test /academy/cohort
"""
from datetime import datetime
from django.utils import timezone
from unittest.mock import MagicMock, patch, call
from ...mixins.new_auth_test_case import AuthTestCase
from ....management.commands.sign_request import Command

from django.core.management.base import OutputWrapper


class AcademyCohortTestSuite(AuthTestCase):
    """
    🔽🔽🔽 With zero Profile
    """

    # When: No app
    # Then: Shouldn't do anything
    @patch('django.core.management.base.OutputWrapper.write', MagicMock())
    def test_no_app(self):
        command = Command()
        result = command.handle(app='1', user=None, method=None, params=None, body=None, headers=None)

        self.assertEqual(result, None)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])
        self.assertEqual(OutputWrapper.write.call_args_list, [
            call('App 1 not found'),
        ])

    # When: With app
    # Then: Print the signature
    @patch('django.core.management.base.OutputWrapper.write', MagicMock())
    def test_sign_jwt(self):
        headers = {
            self.bc.fake.slug(): self.bc.fake.slug(),
            self.bc.fake.slug(): self.bc.fake.slug(),
            self.bc.fake.slug(): self.bc.fake.slug(),
        }
        model = self.bc.database.create(app=1)

        command = Command()

        token = self.bc.fake.slug()
        d = datetime(2023, 8, 3, 4, 2, 58, 992939)
        with patch('hmac.HMAC.hexdigest', MagicMock(return_value=token)):
            with patch('django.utils.timezone.now', MagicMock(return_value=d)):
                result = command.handle(app='1',
                                        user=None,
                                        method=f'{headers}',
                                        params=f'{headers}',
                                        body=f'{headers}',
                                        headers=f'{headers}')

        self.assertEqual(result, None)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])
        self.assertEqual(OutputWrapper.write.call_args_list, [
            call(f'Authorization: Signature App={model.app.slug},'
                 f'Nonce={token},'
                 f'SignedHeaders={";".join(headers.keys())},'
                 f'Date={d.isoformat()}'),
        ])
