import re, urllib
from unittest.mock import patch
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import SlackTestCase
import breathecode.services.slack.commands as commands
from ...exceptions import SlackException
from ...commands.student import execute


class SlackTestSuite(SlackTestCase):

    def test_slack_command___context_is_not_provide_or_is_none(self):
        """Testing  ."""

        with self.assertRaisesMessage(SlackException, 'context-missing'):
            result = execute(users=[])

        with self.assertRaisesMessage(SlackException, 'context-missing'):
            result = execute(users=[], context=None)

    def test_slack_command___user_is_not_authorized(self):
        """Testing  ."""

        data = {'text': 'student', 'user_id': 'name', 'team_id': 'team', 'channel_id': 'test'}

        with self.assertRaisesMessage(SlackException, 'unauthorized-user'):
            result = execute(users=[], context=data)

    def test_slack_command___users_is_an_empty_list(self):
        """Testing  when passing and empty list to users."""

        slack_user = {'slack_id': 'name'}
        slack_team = {'slack_id': 'team'}

        self.bc.database.create(profile_academy=1,
                                slack_user=slack_user,
                                capability='read_student',
                                user=1,
                                role='potato',
                                academy=1,
                                slack_team=slack_team)

        data = {'text': 'student', 'user_id': 'name', 'team_id': 'team', 'channel_id': 'test'}

        with self.assertRaisesMessage(SlackException, 'users-not-provided'):
            result = execute(users=[], context=data)

    def test_slack_command___user_not_registered_in_a_cohort(self):
        """Testing when user is not registered in a cohort."""

        slack_user = {'slack_id': 'name'}
        slack_team = {'slack_id': 'team'}

        self.bc.database.create(profile_academy=1,
                                slack_user=slack_user,
                                capability='read_student',
                                user=1,
                                role='potato',
                                academy=1,
                                slack_team=slack_team)

        data = {
            'text': 'student <@fdd2325|244372eew>',
            'user_id': 'name',
            'team_id': 'team',
            'channel_id': 'test'
        }
        with self.assertRaisesMessage(SlackException, 'cohort-user-not-found'):
            result = execute(users=['fdd2325'], context=data)

    def test_slack_command___user_registered_in_a_cohort__without_financial_status_or_educational_status(
            self):
        """Testing when user is registered in a cohort."""

        slack_users = [{'slack_id': 'name'}, {'slack_id': 'percybrown', 'user_id': 2}]
        slack_team = {'slack_id': 'team'}
        cohort_user = {'user_id': 2}

        model = self.bc.database.create(profile_academy=1,
                                        slack_user=slack_users,
                                        capability='read_student',
                                        user=2,
                                        role='STUDENT',
                                        academy=1,
                                        slack_team=slack_team,
                                        cohort_user=cohort_user)

        data = {
            'text': 'student <@percybrown|244372eew>',
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
                    f'\n*Student Name:* {model.user[1].first_name} {model.user[1].last_name}\n*Github*: not set\n*Phone*: not set\n*Email:* '\
                        f'{model.user[1].email}\n*Cohorts:*\n```\n- {model.cohort.name}: 🎓Not set and 💰Not set\n```\n'
                },
                'accessory': {
                    'type': 'image',
                    'image_url': '/static/img/avatar.png',
                    'alt_text': f'{model.user[1].first_name} {model.user[1].last_name}',

                }
            }]
        }

        result = execute(users=['percybrown'], context=data)

        self.assertEqual(result, expected)

    def test_slack_command___user_registered_in_two_cohorts__with_financial_status_and_educational_status(
            self):
        """Testing when user is registered in a cohort."""

        slack_users = [{'slack_id': 'name'}, {'slack_id': 'percybrown', 'user_id': 2}]
        slack_team = {'slack_id': 'team'}
        cohort_user = [{
            'user_id': 2,
            'finantial_status': 'FULLY_PAID',
            'educational_status': 'ACTIVE'
        }, {
            'user_id': 2,
            'finantial_status': 'UP_TO_DATE',
            'educational_status': 'POSTPONED',
            'cohort_id': 2
        }]

        model = self.bc.database.create(profile_academy=1,
                                        slack_user=slack_users,
                                        capability='read_student',
                                        user=2,
                                        role='STUDENT',
                                        academy=1,
                                        slack_team=slack_team,
                                        cohort_user=cohort_user,
                                        cohort=2)

        data = {
            'text': 'student <@percybrown|244372eew>',
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
                    f'\n*Student Name:* {model.user[1].first_name} {model.user[1].last_name}\n*Github*: not '\
                    f'set\n*Phone*: not set\n*Email:* {model.user[1].email}\n*Cohorts:*\n```\n- '\
                    f'{model.cohort[0].name}: 🎓ACTIVE and 💰FULLY PAID\n- {model.cohort[1].name}: 🎓POSTPONED '\
                    f'and 💰UP TO DATE\n```\n'
                },
                'accessory': {
                    'type': 'image',
                    'image_url': '/static/img/avatar.png',
                    'alt_text': f'{model.user[1].first_name} {model.user[1].last_name}',

                }
            }]
        }

        result = execute(users=['percybrown'], context=data)

        self.assertEqual(result, expected)

    def test_slack_command___user_registered_in_two_different_cohorts__with_financial_status_and_educational_status(
            self):
        """Testing when user is registered in two different cohorts with financial and educational status."""

        slack_users = [{'slack_id': 'name'}, {'slack_id': 'percybrown', 'user_id': 2}]
        slack_team = {'slack_id': 'team'}
        cohort_user = [{
            'user_id': 2,
            'finantial_status': 'FULLY_PAID',
            'educational_status': 'ACTIVE'
        }, {
            'user_id': 2,
            'finantial_status': 'UP_TO_DATE',
            'educational_status': 'POSTPONED',
            'cohort_id': 2
        }]

        model = self.bc.database.create(profile_academy=1,
                                        slack_user=slack_users,
                                        capability='read_student',
                                        user=2,
                                        role='STUDENT',
                                        academy=1,
                                        slack_team=slack_team,
                                        cohort_user=cohort_user,
                                        cohort=2)

        data = {
            'text': 'student <@percybrown|244372eew>',
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
                    f'\n*Student Name:* {model.user[1].first_name} {model.user[1].last_name}\n*Github*: not '\
                    f'set\n*Phone*: not set\n*Email:* {model.user[1].email}\n*Cohorts:*\n```\n- '\
                    f'{model.cohort[0].name}: 🎓ACTIVE and 💰FULLY PAID\n- {model.cohort[1].name}: 🎓POSTPONED '\
                    f'and 💰UP TO DATE\n```\n'
                },
                'accessory': {
                    'type': 'image',
                    'image_url': '/static/img/avatar.png',
                    'alt_text': f'{model.user[1].first_name} {model.user[1].last_name}',

                }
            }]
        }

        result = execute(users=['percybrown'], context=data)
        self.assertEqual(result, expected)
