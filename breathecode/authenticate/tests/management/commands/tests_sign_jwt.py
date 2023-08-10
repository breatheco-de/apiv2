"""
Test /academy/cohort
"""
import os
import random
import logging
from unittest.mock import MagicMock, patch, call
from ...mixins.new_auth_test_case import AuthTestCase
from ....management.commands.sign_jwt import Command

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
        result = command.handle(app='1', user=None)

        self.assertEqual(result, None)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])
        self.assertEqual(OutputWrapper.write.call_args_list, [
            call('App 1 not found'),
        ])

    # When: With app
    # Then: Print the token
    @patch('django.core.management.base.OutputWrapper.write', MagicMock())
    def test_sign_jwt(self):
        model = self.bc.database.create(app=1)

        command = Command()

        token = self.bc.fake.slug()
        with patch('jwt.encode', MagicMock(return_value=token)):
            result = command.handle(app='1', user=None)

        self.assertEqual(result, None)
        self.assertEqual(self.bc.database.list_of('authenticate.UserInvite'), [])
        self.assertEqual(OutputWrapper.write.call_args_list, [
            call(f'Authorization: Link App={model.app.slug},'
                 f'Token={token}'),
        ])
