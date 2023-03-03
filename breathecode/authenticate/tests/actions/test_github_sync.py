"""
Test mentorhips
"""
import json
from breathecode.authenticate.models import Token
from unittest.mock import MagicMock, call, patch
from ...models import GithubAcademyUser
from ..mixins.new_auth_test_case import AuthTestCase
from ...actions import add_to_organization, remove_from_organization, sync_organization_members
from breathecode.utils.validation_exception import ValidationException


def get_org_members():
    return [{'login': 'some-github-username'}, {'login': 'second-username'}]


class SyncGithubUsersTestSuite(AuthTestCase):

    def test_add_to_organization_no_cohort(self):
        """
        When a student enters into a cohort, but he was not in the academy
        """

        models = self.bc.database.create(user=True, cohort=True)
        with self.assertRaises(ValidationException) as context:
            add_to_organization(models.cohort.id, models.user.id)

        self.assertEqual(context.exception.slug, 'invalid-cohort-user')

    def test_add_to_organization_success(self):
        """
        When a student enters into a cohort, but he was not in the academy
        """

        models = self.bc.database.create(user=True, cohort=True, cohort_user=True)
        result = add_to_organization(models.cohort.id, models.user.id)
        self.assertEqual(result, True)

        users = self.bc.database.list_of('authenticate.GithubAcademyUser')
        self.assertEqual(len(users), 1)
        self.assertEqual(models.user.id, users[0]['id'])
        self.assertEqual('PENDING', users[0]['storage_status'])
        self.assertEqual('ADD', users[0]['storage_action'])

    def test_add_to_organization_already_added(self):
        """
        No need to double add student if it was already added previously
        """

        models = self.bc.database.create(user=True,
                                         cohort=True,
                                         cohort_user=True,
                                         github_academy_user={'storage_status': 'SYNCHED'})

        result = add_to_organization(models.cohort.id, models.user.id)
        self.assertEqual(result, True)

        users = self.bc.database.list_of('authenticate.GithubAcademyUser')
        self.assertEqual('SYNCHED', users[0]['storage_status'])
        self.assertEqual('ADD', users[0]['storage_action'])

    def test_add_to_organization_success_previously_errored(self):
        """
        It there was a previous error, we should still try and re-attempt
        """

        models = self.bc.database.create(user=True,
                                         cohort=True,
                                         cohort_user=True,
                                         github_academy_user={'storage_status': 'ERROR'})

        result = add_to_organization(models.cohort.id, models.user.id)
        self.assertEqual(result, True)

        users = self.bc.database.list_of('authenticate.GithubAcademyUser')
        self.assertEqual('PENDING', users[0]['storage_status'])
        self.assertEqual('ADD', users[0]['storage_action'])

    def test_remove_from_organization__no_cohort(self):

        models = self.bc.database.create(
            user=True,
            cohort=True,
            # cohort_user=True,
            # github_academy_user={ 'storage_status': 'ERROR'}
        )

        with self.assertRaises(ValidationException) as context:
            remove_from_organization(models.cohort.id, models.user.id)

        self.assertEqual(context.exception.slug, 'invalid-cohort-user')

    def test_remove_from_organization__no_org_user(self):
        """
        If user its not part of an organization, it cannot be removed
        """

        models = self.bc.database.create(
            user=True,
            cohort=True,
            cohort_user=True,
            # github_academy_user={ 'storage_status': 'ERROR'}
        )

        with self.assertRaises(ValidationException) as context:
            remove_from_organization(models.cohort.id, models.user.id)

        self.assertEqual(context.exception.slug, 'user-not-found-in-org')

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test_remove_from_organization__still_active(self):
        """
        Trying to remove someone that its still active in any cohort
        show give an error
        """

        models = self.bc.database.create(
            user=True,
            cohort=True,
            cohort_user=True,
            cohort_user_kwargs={'educational_status': 'ACTIVE'},
        )

        with self.assertRaises(ValidationException) as context:
            remove_from_organization(models.cohort.id, models.user.id)

        self.assertEqual(context.exception.slug, 'still-active')

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    @patch('django.db.models.signals.post_save.send', MagicMock())
    def test_remove_from_organization__still_active_another_org(self):
        """
        Trying to remove someone that its still active in another
        cohort from the same academy
        """

        models = self.bc.database.create(
            user=True,
            cohort=True,
            cohort_user=True,
            cohort_user_kwargs={'educational_status': 'ACTIVE'},
        )

        models2 = self.bc.database.create(
            cohort=True,
            cohort_user=True,
            cohort_kwargs={'academy': models.academy},
            cohort_user_kwargs={
                'user': models.user,
            },
        )

        with self.assertRaises(ValidationException) as context:
            remove_from_organization(models2.cohort.id, models.user.id)

        self.assertEqual(context.exception.slug, 'still-active')

    @patch('breathecode.services.github.Github.get_org_members', MagicMock(side_effect=get_org_members))
    def test_sync_organization_members__no_sync(self):
        """

        """

        models = self.bc.database.create(academy=True)

        models2 = self.bc.database.create(academy_auth_settings=True,
                                          github_academy_user=True,
                                          academy_auth_settings_kwargs={
                                              'academy': models.academy,
                                              'github_is_sync': False,
                                          },
                                          github_academy_user_kwargs={'academy': models.academy})

        result = sync_organization_members(models.academy.id)
        self.assertEqual(result, False)

    @patch('breathecode.services.github.Github.get_org_members', MagicMock(side_effect=get_org_members))
    def test_sync_organization_members__no_settings(self):
        """

        """

        models = self.bc.database.create(academy=True)

        models2 = self.bc.database.create(github_academy_user=True,
                                          github_academy_user_kwargs={'academy': models.academy})

        result = sync_organization_members(models.academy.id)
        self.assertEqual(result, False)

    @patch('breathecode.services.github.Github.get_org_members', MagicMock(side_effect=get_org_members))
    def test_sync_organization_members__all_must_be_sync(self):
        """
        If all organizations with the same user dont are not in sync, we
        will not sync
        """

        models = self.bc.database.create(academy=True,
                                         academy_auth_settings=True,
                                         github_academy_user=True,
                                         academy_auth_settings_kwargs={
                                             'github_is_sync': True,
                                             'github_username': 'some-username'
                                         })
        models2 = self.bc.database.create(academy=True,
                                          academy_auth_settings=True,
                                          github_academy_user=True,
                                          academy_auth_settings_kwargs={
                                              'github_is_sync': False,
                                              'github_username': 'some-username'
                                          })

        with self.assertRaises(ValidationException) as context:
            sync_organization_members(models.academy.id)

        self.assertEqual(context.exception.slug, 'not-everyone-in-synch')

    @patch('breathecode.services.github.Github.get_org_members', MagicMock(side_effect=get_org_members))
    def test_sync_organization_members_invalid_owner_no_githubcredentials(self):
        """

        """

        models = self.bc.database.create(
            user=True,
            #  user_kwargs={'credentialsgithub': None},
            academy=True,
            academy_auth_settings=True,
            github_academy_user=True,
            academy_auth_settings_kwargs={
                'github_is_sync': True,
                'github_username': 'some-username'
            })

        with self.assertRaises(ValidationException) as context:
            sync_organization_members(models.academy.id)

        self.assertEqual(context.exception.slug, 'invalid-owner')

    @patch('breathecode.services.github.Github.get_org_members', MagicMock(side_effect=get_org_members))
    @patch('breathecode.services.github.Github.invite_org_member', MagicMock())
    @patch('breathecode.services.github.Github.delete_org_member', MagicMock())
    def test_sync_organization_members__no_githubcredentials_marked_as_error(self):
        """
        Any AcademyUser that has not github connection must be marked as error
        """

        models = self.bc.database.create(user=True,
                                         credentials_github=True,
                                         academy=True,
                                         academy_auth_settings=True,
                                         academy_auth_settings_kwargs={
                                             'github_is_sync': True,
                                             'github_username': 'some-username'
                                         })

        models2 = self.bc.database.create(user=True,
                                          credentials_github=False,
                                          github_academy_user=True,
                                          github_academy_user_kwargs={
                                              'storage_status': 'PENDING',
                                              'storage_action': 'ADD',
                                              'academy': models.academy
                                          })

        models3 = self.bc.database.create(user=True,
                                          credentials_github=True,
                                          github_academy_user=True,
                                          github_academy_user_kwargs={
                                              'storage_status': 'PENDING',
                                              'storage_action': 'REMOVE',
                                              'academy': models.academy
                                          })

        sync_organization_members(models.academy.id)

        GithubAcademyUser = self.bc.database.get_model('authenticate.GithubAcademyUser')
        users = GithubAcademyUser.objects.filter(user__credentialsgithub__isnull=True).exclude(
            user__isnull=True)
        self.assertEqual(users.count(), 1)
        no_credentials_user = users.first()
        self.assertEqual(no_credentials_user.storage_status, 'ERROR')
        self.assertEqual([l['msg'] for l in no_credentials_user.storage_log],
                         [GithubAcademyUser.create_log('This user needs connect to github')['msg']])

    @patch('breathecode.services.github.Github.get_org_members', MagicMock(side_effect=get_org_members))
    @patch('breathecode.services.github.Github.invite_org_member', MagicMock())
    @patch('breathecode.services.github.Github.delete_org_member', MagicMock())
    def test_sync_organization_members_sync_pending_add(self):
        """
        Users with pending add and delete sync should be invited using the gitpod API
        """

        github_email = 'sam@mail.com'
        models = self.bc.database.create(user=True,
                                         credentials_github=True,
                                         academy=True,
                                         academy_auth_settings=True,
                                         academy_auth_settings_kwargs={
                                             'github_is_sync': True,
                                             'github_username': 'some-username'
                                         })

        models2 = self.bc.database.create(user=True,
                                          credentials_github=True,
                                          credentials_github_kwargs={'email': github_email},
                                          github_academy_user=True,
                                          github_academy_user_kwargs={
                                              'storage_status': 'PENDING',
                                              'storage_action': 'ADD',
                                              'academy': models.academy
                                          })

        models3 = self.bc.database.create(
            user=True,
            credentials_github=True,
            # this username is coming from the mock on the top of the file
            credentials_github_kwargs={'username': 'some-github-username'},
            github_academy_user=True,
            github_academy_user_kwargs={
                'storage_status': 'PENDING',
                'storage_action': 'DELETE',
                'academy': models.academy
            })

        sync_organization_members(models.academy.id)

        # test for add
        GithubAcademyUser = self.bc.database.get_model('authenticate.GithubAcademyUser')
        user = GithubAcademyUser.objects.get(id=models2.github_academy_user.id)
        self.assertEqual(user.storage_status, 'SYNCHED')
        self.assertEqual(user.storage_action, 'ADD')
        self.assertEqual([l['msg'] for l in user.storage_log],
                         [GithubAcademyUser.create_log(f'Sent invitation to {github_email}')['msg']])

        # test for success
        user = GithubAcademyUser.objects.get(id=models3.github_academy_user.id)
        self.assertEqual(user.storage_status, 'SYNCHED')
        self.assertEqual(user.storage_action, 'DELETE')
        self.assertEqual(
            [l['msg'] for l in user.storage_log],
            [GithubAcademyUser.create_log(f'Successfully deleted in github organization')['msg']])

    @patch('breathecode.services.github.Github.get_org_members', MagicMock(side_effect=get_org_members))
    @patch('breathecode.services.github.Github.invite_org_member', MagicMock())
    @patch('breathecode.services.github.Github.delete_org_member', MagicMock())
    def test_sync_organization_members_succesfully_deleted(self):
        """
        User was found in github and deleted from both, organiztion and github
        """

        github_email = 'sam@mail.com'
        models = self.bc.database.create(user=True,
                                         credentials_github=True,
                                         academy=True,
                                         academy_auth_settings=True,
                                         academy_auth_settings_kwargs={
                                             'github_is_sync': True,
                                             'github_username': 'academy-username'
                                         })

        models3 = self.bc.database.create(
            user=True,
            credentials_github=True,
            credentials_github_kwargs={
                # this has to match the mocked response from github api
                'username': 'some-github-username'
            },
            github_academy_user=True,
            github_academy_user_kwargs={
                'storage_status': 'PENDING',
                'storage_action': 'DELETE',
                'academy': models.academy
            })

        sync_organization_members(models.academy.id)

        # already deleted from github
        user = GithubAcademyUser.objects.get(id=models3.github_academy_user.id)
        self.assertEqual(user.storage_status, 'SYNCHED')
        self.assertEqual(user.storage_action, 'DELETE')
        self.assertEqual(
            [l['msg'] for l in user.storage_log],
            [GithubAcademyUser.create_log(f'Successfully deleted in github organization')['msg']])

    @patch('breathecode.services.github.Github.get_org_members', MagicMock(side_effect=get_org_members))
    @patch('breathecode.services.github.Github.invite_org_member', MagicMock())
    @patch('breathecode.services.github.Github.delete_org_member', MagicMock())
    def test_sync_organization_members_already_deleted(self):
        """
        User was already deleted because its github username was not included in the github API incoming usernames
        """

        github_email = 'sam@mail.com'
        models = self.bc.database.create(user=True,
                                         credentials_github=True,
                                         academy=True,
                                         academy_auth_settings=True,
                                         academy_auth_settings_kwargs={
                                             'github_is_sync': True,
                                             'github_username': 'academy-username'
                                         })

        models3 = self.bc.database.create(
            user=True,
            credentials_github=True,
            credentials_github_kwargs={
                # username dont match the mocked github api response on purpose
                'username': 'some-github-username-dont-match'
            },
            github_academy_user=True,
            github_academy_user_kwargs={
                'storage_status': 'PENDING',
                'storage_action': 'DELETE',
                'academy': models.academy
            })

        sync_organization_members(models.academy.id)

        # already deleted from github
        user = GithubAcademyUser.objects.get(id=models3.github_academy_user.id)
        self.assertEqual(user.storage_status, 'SYNCHED')
        self.assertEqual(user.storage_action, 'DELETE')
        self.assertEqual([l['msg'] for l in user.storage_log],
                         [GithubAcademyUser.create_log(f'User was already deleted from github')['msg']])

    @patch('breathecode.services.github.Github.get_org_members', MagicMock(side_effect=get_org_members))
    @patch('breathecode.services.github.Github.invite_org_member', MagicMock())
    @patch('breathecode.services.github.Github.delete_org_member', MagicMock())
    def test_sync_organization__unknown_github_users(self):
        """
        Some other users found on github added as unknown on the organization
        """

        github_email = 'sam@mail.com'
        models = self.bc.database.create(user=True,
                                         credentials_github=True,
                                         academy=True,
                                         academy_auth_settings=True,
                                         academy_auth_settings_kwargs={
                                             'github_is_sync': True,
                                             'github_username': 'academy-username'
                                         })

        models2 = self.bc.database.create(user=True,
                                          credentials_github=True,
                                          credentials_github_kwargs={'username': 'second-username'},
                                          academy=True,
                                          academy_auth_settings=True,
                                          academy_auth_settings_kwargs={
                                              'github_is_sync': True,
                                              'github_username': models.academy_auth_settings.github_username
                                          })

        sync_organization_members(models.academy.id)

        # already deleted from github
        unknown = GithubAcademyUser.objects.filter(academy__id=models.academy.id, storage_status='UNKNOWN')
        print('unknown', unknown)
        self.assertEqual(unknown.count(), 2)
