import re, urllib
from unittest.mock import patch
from rest_framework import status
from ..mixins import SlackTestCase
import breathecode.services.slack.commands as commands
from ...exceptions import SlackException
from ...commands.cohort import execute


class SlackTestSuite(SlackTestCase):

    def test_slack_command___context_is_not_provided_or_is_none(self):
        """Testing when context is None or not provided."""

        with self.assertRaisesMessage(SlackException, 'context-missing'):
            result = execute(users=[])

        with self.assertRaisesMessage(SlackException, 'context-missing'):
            result = execute(users=[], context=None)

    def test_slack_command___user_is_not_authorized(self):
        """Testing when user is not authorized."""

        data = {'text': 'cohort', 'user_id': 'name', 'team_id': 'team', 'channel_id': 'test'}

        with self.assertRaisesMessage(SlackException, 'unauthorized-user'):
            result = execute(users=[], context=data)

    def test_slack_command___cohort_does_not_exist(self):
        """Testing when cohort does not exist."""

        slack_user = {'slack_id': 'name'}
        slack_team = {'slack_id': 'team'}

        self.bc.database.create(profile_academy=1,
                                slack_user=slack_user,
                                capability='read_cohort',
                                user=1,
                                role='potato',
                                academy=1,
                                slack_team=slack_team)

        data = {'text': 'cohort', 'user_id': 'name', 'team_id': 'team', 'channel_id': 'test'}

        with self.assertRaisesMessage(SlackException, 'cohort-not-found'):
            result = execute(users=[], context=data)

    def test_slack_command___cohort_does_exist_but_not_associated_with_slack_channel(self):
        """Testing when cohort does exist but not associated with slack channel."""

        slack_user = {'slack_id': 'name'}
        slack_team = {'slack_id': 'team'}

        self.bc.database.create(profile_academy=1,
                                slack_user=slack_user,
                                capability='read_cohort',
                                user=1,
                                role='potato',
                                academy=1,
                                slack_team=slack_team)

        data = {
            'text': 'cohort <@fdd2325|244372eew>',
            'user_id': 'name',
            'team_id': 'team',
            'channel_id': 'test'
        }
        with self.assertRaisesMessage(SlackException, 'cohort-not-found'):
            result = execute(users=['fdd2325'], context=data)

    def test_slack_command___cohort_does_exist_and_associated_with_slack_channel(self):
        """Testing when cohort exists and is associated with slack channel"""

        slack_users = [{'slack_id': 'name'}]
        slack_team = {'slack_id': 'team'}
        slack_channel = {'slack_id': 'test'}
        cohort_user = {'user_id': 1}

        model = self.bc.database.create(profile_academy=1,
                                        slack_user=slack_users,
                                        capability='read_cohort',
                                        user=1,
                                        role='hello',
                                        academy=1,
                                        slack_team=slack_team,
                                        cohort_user=cohort_user,
                                        slack_channel=slack_channel)

        data = {
            'text': 'cohort <@percybrown|244372eew>',
            'user_id': 'name',
            'team_id': 'team',
            'channel_id': 'test'
        }
        expected = {
            'blocks': [{
                'type': 'section',
                'text': {
                    'type':
                    'mrkdwn',
                    'text':
                    '\n'.join([
                        '',
                        f'*Cohort name:* {model.cohort.name}',
                        f'*Start Date:* {model.cohort.kickoff_date}',
                        f'*End Date:* {model.cohort.ending_date}',
                        f'*Current day:* {model.cohort.current_day}',
                        f'*Stage:* {model.cohort.stage}',
                        f'*Teachers:* ',
                        '',
                    ])
                }
            }]
        }

        result = execute(users=['percybrown'], context=data)

        self.assertEqual(result, expected)

    def test_slack_command___cohort_does_exist_and_role_is_teacher(self):
        """Testing when cohort exists and role is teacher"""

        slack_users = [{'slack_id': 'name'}]
        slack_team = {'slack_id': 'team'}
        slack_channel = {'slack_id': 'test'}
        cohort_user = {'role': 'TEACHER'}

        model = self.bc.database.create(profile_academy=1,
                                        slack_user=slack_users,
                                        capability='read_cohort',
                                        user=1,
                                        role='teacher',
                                        academy=1,
                                        slack_team=slack_team,
                                        cohort_user=cohort_user,
                                        slack_channel=slack_channel)

        teachers = [model.cohort_user]

        teacher_role = ', '.join([cu.user.first_name + ' ' + cu.user.last_name for cu in teachers])

        data = {
            'text': 'cohort <@percybrown|244372eew>',
            'user_id': 'name',
            'team_id': 'team',
            'channel_id': 'test'
        }
        expected = {
            'blocks': [{
                'type': 'section',
                'text': {
                    'type':
                    'mrkdwn',
                    'text':
                    '\n'.join([
                        '',
                        f'*Cohort name:* {model.cohort.name}',
                        f'*Start Date:* {model.cohort.kickoff_date}',
                        f'*End Date:* {model.cohort.ending_date}',
                        f'*Current day:* {model.cohort.current_day}',
                        f'*Stage:* {model.cohort.stage}',
                        f'*Teachers:* {teacher_role}',
                        '',
                    ])
                }
            }]
        }

        result = execute(users=['percybrown'], context=data)

        self.assertEqual(result, expected)
