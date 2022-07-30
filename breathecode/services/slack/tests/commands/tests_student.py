import random
from unittest.mock import MagicMock, call, patch

from breathecode.tests.mixins.breathecode_mixin.breathecode import fake
from ..mixins import SlackTestCase
from ...exceptions import SlackException
from ...commands.student import execute

API_URL = fake.url()[0:-1]


def profile_fields(data={}):
    return {
        'avatar_url': None,
        'bio': None,
        'blog': None,
        'github_username': None,
        'id': 0,
        'linkedin_url': None,
        'phone': '',
        'portfolio_url': None,
        'show_tutorial': True,
        'twitter_username': None,
        'user_id': 0,
        **data,
    }


def apply_get_env(configuration={}):
    def get_env(key, value=None):
        return configuration.get(key, value)

    return get_env


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

        avatar_number = random.randint(1, 31)
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
                    'image_url': f'/static/img/avatar-{avatar_number}.png',
                    'alt_text': f'{model.user[1].first_name} {model.user[1].last_name}',

                }
            }]
        }

        with patch('random.randint') as mock:
            mock.return_value = avatar_number
            result = execute(users=['percybrown'], context=data)

            self.assertEqual(random.randint.call_args_list, [call(1, 31)])

        self.assertEqual(result, expected)
        self.assertEqual(self.bc.database.list_of('authenticate.Profile'), [])

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

        avatar_number = random.randint(1, 31)
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
                    'image_url': f'/static/img/avatar-{avatar_number}.png',
                    'alt_text': f'{model.user[1].first_name} {model.user[1].last_name}',

                }
            }]
        }

        with patch('random.randint') as mock:
            mock.return_value = avatar_number
            result = execute(users=['percybrown'], context=data)

            self.assertEqual(random.randint.call_args_list, [call(1, 31)])

        self.assertEqual(result, expected)
        self.assertEqual(self.bc.database.list_of('authenticate.Profile'), [])

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

        avatar_number = random.randint(1, 31)
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
                    'image_url': f'/static/img/avatar-{avatar_number}.png',
                    'alt_text': f'{model.user[1].first_name} {model.user[1].last_name}',

                }
            }]
        }

        with patch('random.randint') as mock:
            mock.return_value = avatar_number
            result = execute(users=['percybrown'], context=data)

            self.assertEqual(random.randint.call_args_list, [call(1, 31)])

        self.assertEqual(result, expected)
        self.assertEqual(self.bc.database.list_of('authenticate.Profile'), [])

    """
    🔽🔽🔽 With two CohortUser and one Profile, with right financial_status and educational_status, profile
    empty
    """

    @patch('os.getenv', MagicMock(side_effect=apply_get_env({'API_URL': API_URL})))
    def test_slack_command___with_profile_empty(self):
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

        profile = {'user_id': 2}
        model = self.bc.database.create(profile_academy=1,
                                        profile=profile,
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

        avatar_number = random.randint(1, 31)
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
                    'image_url': f'{API_URL}/static/img/avatar-{avatar_number}.png',
                    'alt_text': f'{model.user[1].first_name} {model.user[1].last_name}',

                }
            }]
        }

        with patch('random.randint') as mock:
            mock.return_value = avatar_number
            result = execute(users=['percybrown'], context=data)

            self.assertEqual(random.randint.call_args_list, [call(1, 31)])

        self.assertEqual(result, expected)
        self.assertEqual(self.bc.database.list_of('authenticate.Profile'), [
            profile_fields({
                'id': 1,
                'user_id': 2,
                'avatar_url': f'{API_URL}/static/img/avatar-{avatar_number}.png',
            }),
        ])

    """
    🔽🔽🔽 With two CohortUser and one Profile, with right financial_status and educational_status, profile
    set
    """

    @patch('os.getenv', MagicMock(side_effect=apply_get_env({'API_URL': API_URL})))
    def test_slack_command___with_profile_set(self):
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

        github_username = self.bc.fake.slug()
        phone = self.bc.fake.phone_number()
        profile = {
            'user_id': 2,
            'github_username': github_username,
            'phone': phone,
        }

        model = self.bc.database.create(profile_academy=1,
                                        profile=profile,
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

        avatar_number = random.randint(1, 31)
        expected = {
            'blocks': [{
                'type': 'section',
                'text': {
                    'type':
                    'mrkdwn',
                    'text':
                    f'\n*Student Name:* {model.user[1].first_name} {model.user[1].last_name}\n*Github*: '\
                    f'{github_username}\n*Phone*: {phone}\n*Email:* {model.user[1].email}\n*Cohorts:*\n```\n- '\
                    f'{model.cohort[0].name}: 🎓ACTIVE and 💰FULLY PAID\n- {model.cohort[1].name}: 🎓POSTPONED '\
                    f'and 💰UP TO DATE\n```\n'
                },
                'accessory': {
                    'type': 'image',
                    'image_url': f'{API_URL}/static/img/avatar-{avatar_number}.png',
                    'alt_text': f'{model.user[1].first_name} {model.user[1].last_name}',

                }
            }]
        }

        with patch('random.randint') as mock:
            mock.return_value = avatar_number
            result = execute(users=['percybrown'], context=data)

            self.assertEqual(random.randint.call_args_list, [call(1, 31)])

        self.assertEqual(result, expected)
        self.assertEqual(self.bc.database.list_of('authenticate.Profile'), [
            profile_fields({
                'id': 1,
                'user_id': 2,
                'avatar_url': f'{API_URL}/static/img/avatar-{avatar_number}.png',
                'github_username': github_username,
                'phone': phone,
            }),
        ])
