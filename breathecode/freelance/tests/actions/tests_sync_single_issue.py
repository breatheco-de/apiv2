"""
Test mentorhips
"""
import json
from ..mixins import FreelanceTestCase
from ...actions import sync_single_issue
from unittest.mock import MagicMock, call, patch
from logging import Logger


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
    def test_sync_single_issue(self):
        """
        When the mentor gets into the room before the mentee
        if should create a room with status 'pending'
        """

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
    def test_sync_single_issue_asd(self):
        """
        When the mentor gets into the room before the mentee
        if should create a room with status 'pending'
        """

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
    def test_sync_single_issue_testthree(self):
        """
        When the mentor gets into the room before the mentee
        if should create a room with status 'pending'
        """

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
