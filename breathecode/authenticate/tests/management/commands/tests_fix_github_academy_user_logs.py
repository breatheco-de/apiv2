import random
from unittest.mock import MagicMock, patch
from django.contrib.auth.models import Group
from breathecode.authenticate.management.commands.fix_github_academy_user_logs import Command
from django.utils import timezone
from ...mixins.new_auth_test_case import AuthTestCase

T1 = timezone.now()
T2 = T1 + timezone.timedelta(days=1)
T3 = T2 + timezone.timedelta(days=1)
T4 = T3 + timezone.timedelta(days=1)


class TokenTestSuite(AuthTestCase):
    # When: running the command and there are nothing to migrate
    # Then: it should don't do anything
    def test__nothing_to_migrate(self):
        command = Command()
        command.handle()

        self.assertEqual(self.bc.database.list_of('authenticate.GithubAcademyUserLog'), [])

    # When: have a list of things to migrate
    # Then: it should migrate all the things
    def test__list_of_stuff_to_migrate(self):
        github_academy_users = [{'user_id': n + 1} for n in range(2)]
        base = self.bc.database.create(user=2, github_academy_user=github_academy_users)

        storage_statuses = ['PENDING', 'SYNCHED', 'ERROR', 'UNKNOWN', 'PAYMENT_CONFLICT']
        storage_actions = ['ADD', 'INVITE', 'DELETE', 'IGNORE']

        github_academy_user_logs = [{
            'academy_user_id': n + 1,
            'valid_until': None,
            'storage_status': random.choice(storage_statuses),
            'storage_action': random.choice(storage_actions),
        } for n in range(2)]

        with patch('django.utils.timezone.now', MagicMock(return_value=T1)):
            model1 = self.bc.database.create(github_academy_user=base.github_academy_user,
                                             github_academy_user_log=github_academy_user_logs)

        for n in range(2):
            github_academy_user_logs[n]['storage_status'] = random.choice(storage_statuses)
            github_academy_user_logs[n]['storage_action'] = random.choice(storage_actions)

        with patch('django.utils.timezone.now', MagicMock(return_value=T2)):
            model2 = self.bc.database.create(github_academy_user=base.github_academy_user,
                                             github_academy_user_log=github_academy_user_logs)

        for n in range(2):
            github_academy_user_logs[n]['storage_status'] = random.choice(storage_statuses)
            github_academy_user_logs[n]['storage_action'] = random.choice(storage_actions)

        with patch('django.utils.timezone.now', MagicMock(return_value=T3)):
            model3 = self.bc.database.create(github_academy_user=base.github_academy_user,
                                             github_academy_user_log=github_academy_user_logs)

        command = Command()
        with patch('django.utils.timezone.now', MagicMock(return_value=T4)):
            command.handle()

        self.assertEqual(self.bc.database.list_of('authenticate.GithubAcademyUserLog'), [
            *[{
                **self.bc.format.to_dict(x),
                'valid_until': T2,
            } for x in model1.github_academy_user_log],
            *[{
                **self.bc.format.to_dict(x),
                'valid_until': T3,
            } for x in model2.github_academy_user_log],
            *[{
                **self.bc.format.to_dict(x),
                'valid_until': None,
            } for x in model3.github_academy_user_log],
        ])
