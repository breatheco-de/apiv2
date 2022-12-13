"""
Test mentorhips
"""
import json
from ..mixins import FreelanceTestCase
from ...actions import sync_single_issue
from unittest.mock import MagicMock, call, patch
from logging import Logger
import random


def issue_item(data={}):
    return {
        'academy_id': None,
        'author_id': None,
        'bill_id': None,
        'body': 'team-learn-plan',
        'duration_in_hours': 0.0,
        'duration_in_minutes': 0.0,
        'freelancer_id': 1,
        'github_number': None,
        'github_state': None,
        'id': 1,
        'invoice_id': None,
        'node_id': '1',
        'repository_url': None,
        'status': 'DRAFT',
        'status_message': None,
        'title': 'dinner-surface-need',
        'url': 'http://miller.com/',
        **data
    }


class GetOrCreateSessionTestSuite(FreelanceTestCase):

    @patch('logging.Logger.debug', MagicMock())
    def test_IssueWithNoId(self):

        # models1 = self.bc.database.create(syllabus=True,
        #                                   syllabus_version={'json': data1},
        #                                   authenticate=True,
        #                                   capability='crud_syllabus')

        result = sync_single_issue({})
        self.assertEqual(result, None)
        self.assertEqual(self.bc.database.list_of('freelance.Issue'), [])

        print(Logger.debug.call_args_list)
        self.assertEqual(Logger.debug.call_args_list, [
            call(
                'Impossible to identify issue because it does not have a node_id (number:None), ignoring synch: {}'
            )
        ])

    @patch('logging.Logger.debug', MagicMock())
    def test_IssueWithFakeSlug(self):

        # models1 = self.bc.database.create(syllabus=True,
        #                                   syllabus_version={'json': data1},
        #                                   authenticate=True,
        #                                   capability='crud_syllabus')

        with self.assertRaisesMessage(Exception, 'There was no freelancer associated with this issue'):

            result = sync_single_issue({
                'node_id': 1,
                'title': self.bc.fake.slug(),
                'body': self.bc.fake.slug(),
                'html_url': self.bc.fake.url()
            })

        self.assertEqual(self.bc.database.list_of('freelance.Issue'), [])

        print(Logger.debug.call_args_list)
        self.assertEqual(Logger.debug.call_args_list, [])

    @patch('logging.Logger.debug', MagicMock())
    def test_IssueWith_freelancer(self):

        models1 = self.bc.database.create(freelancer=1)

        title = self.bc.fake.slug()
        body = self.bc.fake.slug()
        url = self.bc.fake.url()

        # with self.assertRaisesMessage(Exception, 'There was no freelancer associated with this issue'):
        print(models1.freelancer)
        result = sync_single_issue({
            'node_id': 1,
            'title': title,
            'body': body,
            'html_url': url
        },
                                   freelancer=models1.freelancer)

        self.assertEqual(self.bc.database.list_of('freelance.Issue'), [
            issue_item({
                'node_id': str(1),
                'title': title,
                'body': body,
                'url': url
            }),
        ])

        print(Logger.debug.call_args_list)
        self.assertEqual(Logger.debug.call_args_list, [])

    @patch('logging.Logger.debug', MagicMock())
    def testing_hours(self):

        models1 = self.bc.database.create(freelancer=1)

        title = self.bc.fake.slug()
        hours = random.random() * 50
        minutes = hours * 60
        body = f'<hrs>{hours}</hrs>'
        url = self.bc.fake.url()

        # with self.assertRaisesMessage(Exception, 'There was no freelancer associated with this issue'):

        result = sync_single_issue({
            'node_id': 1,
            'title': title,
            'body': body,
            'html_url': url,
        },
                                   freelancer=models1.freelancer)

        self.assertEqual(self.bc.database.list_of('freelance.Issue'), [
            issue_item({
                'node_id': str(1),
                'title': title,
                'body': body,
                'url': url,
                'duration_in_hours': hours,
                'duration_in_minutes': minutes
            }),
        ])

        print(Logger.debug.call_args_list)
        self.assertEqual(Logger.debug.call_args_list,
                         [call(f'Updating issue 1 (None) hrs with {hours}, found <hrs> tag on updated body')])

    @patch('logging.Logger.debug', MagicMock())
    def testing_different_hours(self):

        models1 = self.bc.database.create(freelancer=1)

        title = self.bc.fake.slug()
        hours = random.random() * 50
        another = random.random() * 50
        minutes = hours * 60
        issue_body = f'<hrs>{another}</hrs>'
        comment_body = f'<hrs>{hours}</hrs> <status>comment</status>'
        url = self.bc.fake.url()

        # with self.assertRaisesMessage(Exception, 'There was no freelancer associated with this issue'):

        result = sync_single_issue({
            'node_id': 1,
            'title': title,
            'body': issue_body,
            'html_url': url,
        },
                                   freelancer=models1.freelancer,
                                   comment={'body': comment_body})

        self.assertEqual(self.bc.database.list_of('freelance.Issue'), [
            issue_item({
                'node_id': str(1),
                'title': title,
                'body': issue_body,
                'url': url,
                'duration_in_hours': hours,
                'duration_in_minutes': minutes,
                'status_message': 'The status COMMENT is not valid',
            }),
        ])

        print(Logger.debug.call_args_list)
        self.assertEqual(Logger.debug.call_args_list, [
            call(f'Updating issue 1 (None) hrs with {another}, found <hrs> tag on updated body'),
            call(f'Updating issue 1 (None) hrs with {hours}, found <hrs> tag on new comment'),
            call('The status COMMENT is not valid')
        ])

    @patch('logging.Logger.debug', MagicMock())
    def testing_correct_status_with_hours(self):
        """
        When the mentor gets into the room before the mentee
        if should create a room with status 'pending'
        """

        models1 = self.bc.database.create(freelancer=1)

        status = random.choice(['IGNORED', 'DRAFT', 'TODO', 'DOING', 'DONE'])
        title = self.bc.fake.slug()
        hours = random.random() * 50
        another = random.random() * 50
        minutes = hours * 60
        issue_body = f'<hrs>{another}</hrs>'
        comment_body = f'<hrs>{hours}</hrs> <status>{status}</status>'
        url = self.bc.fake.url()

        # with self.assertRaisesMessage(Exception, 'There was no freelancer associated with this issue'):

        result = sync_single_issue({
            'node_id': 1,
            'title': title,
            'body': issue_body,
            'html_url': url,
        },
                                   freelancer=models1.freelancer,
                                   comment={'body': comment_body})

        self.assertEqual(self.bc.database.list_of('freelance.Issue'), [
            issue_item({
                'node_id': str(1),
                'title': title,
                'body': issue_body,
                'url': url,
                'duration_in_hours': hours,
                'duration_in_minutes': minutes,
                'status': status,
            }),
        ])

        print(Logger.debug.call_args_list)
        self.assertEqual(Logger.debug.call_args_list, [
            call(f'Updating issue 1 (None) hrs with {another}, found <hrs> tag on updated body'),
            call(f'Updating issue 1 (None) hrs with {hours}, found <hrs> tag on new comment'),
            call(f'Updating issue 1 (None) status to {status} found <status> tag on new comment')
        ])

    @patch('logging.Logger.debug', MagicMock())
    def testing_Assignee_FreelancerIsNone(self):

        with self.assertRaisesMessage(Exception, 'There was no freelancer associated with this issue'):
            models1 = self.bc.database.create(freelancer=None)

            status = random.choice(['IGNORED', 'DRAFT', 'TODO', 'DOING', 'DONE'])
            title = self.bc.fake.slug()
            hours = random.random() * 50
            another = random.random() * 50
            minutes = hours * 60
            assignees = random.random() * 50
            issue_body = f'<hrs>{another}</hrs>'
            comment_body = f'<hrs>{hours}</hrs> <status>{status}</status>'
            url = self.bc.fake.url()

            result = sync_single_issue({
                'node_id': 1,
                'title': title,
                'body': issue_body,
                'html_url': url,
            },
                                       freelancer=None)

            issue_item({
                'node_id': str(1),
                'title': title,
                'body': issue_body,
                'url': url,
                'assignees': assignees,
                'duration_in_hours': hours,
                'duration_in_minutes': minutes,
                'status': status,
            })

            print(Logger.debug.call_args_list)
            self.assertEqual(Logger.debug.call_args_list, [])

    @patch('logging.Logger.debug', MagicMock())
    def testing_AssigneeID_FreelancerIsNone(self):

        models1 = self.bc.database.create(freelancer=None)

        assignment_id = 3
        status = random.choice(['IGNORED', 'DRAFT', 'TODO', 'DOING', 'DONE'])
        title = self.bc.fake.slug()
        hours = random.random() * 50
        another = random.random() * 50
        minutes = hours * 60
        freelancer: None
        assignees = [{'id': assignment_id}]
        assigne = assignees[0]
        issue_body = f'<hrs>{another}</hrs>'
        comment_body = f'<hrs>{hours}</hrs> <status>{status}</status>'
        url = self.bc.fake.url()

        with self.assertRaisesMessage(
                Exception,
                f'Assigned github user: {assigne["id"]} is not a freelancer but is the main user associated to this issue'
        ):
            result = sync_single_issue(
                {
                    'node_id': 1,
                    'title': title,
                    'body': issue_body,
                    'html_url': url,
                    'assignees': assignees,
                },
                freelancer=None)

            issue_item({
                'node_id': str(1),
                'title': title,
                'body': issue_body,
                'url': url,
                'assignees': assignees,
                'freelancer': freelancer,
                'duration_in_hours': hours,
                'duration_in_minutes': minutes,
                'status': status,
            })

            print(Logger.debug.call_args_list)
            self.assertEqual(Logger.debug.call_args_list, [])
