"""
Test Sync Single Issue
"""

import json
from ..mixins import FreelanceTestCase
from ...actions import sync_single_issue
from unittest.mock import MagicMock, call, patch
from logging import Logger
import random


def issue_item(data={}):
    return {
        "academy_id": None,
        "author_id": None,
        "bill_id": None,
        "body": "team-learn-plan",
        "duration_in_hours": 0.0,
        "duration_in_minutes": 0.0,
        "freelancer_id": 1,
        "github_number": None,
        "github_state": None,
        "id": 1,
        "invoice_id": None,
        "node_id": "1",
        "repository_url": None,
        "status": "DRAFT",
        "status_message": None,
        "title": "dinner-surface-need",
        "url": "http://miller.com/",
        **data,
    }


class GetOrCreateSessionTestSuite(FreelanceTestCase):

    @patch("logging.Logger.info", MagicMock())
    def test_IssueWithNoId(self):

        result = sync_single_issue({})
        self.assertEqual(result, None)
        self.assertEqual(self.bc.database.list_of("freelance.Issue"), [])
        self.assertEqual(
            Logger.info.call_args_list,
            [call("Impossible to identify issue because it does not have a node_id (number:None), ignoring synch: {}")],
        )

    @patch("logging.Logger.info", MagicMock())
    def test_IssueWithFakeSlug(self):

        with self.assertRaisesMessage(Exception, "There was no freelancer associated with this issue"):

            result = sync_single_issue(
                {
                    "node_id": 1,
                    "title": self.bc.fake.slug(),
                    "body": self.bc.fake.slug(),
                    "html_url": self.bc.fake.url(),
                }
            )

        self.assertEqual(self.bc.database.list_of("freelance.Issue"), [])

        self.assertEqual(Logger.info.call_args_list, [])

    @patch("logging.Logger.info", MagicMock())
    def test_IssueWith_freelancer(self):

        models1 = self.bc.database.create(freelancer=1)
        Logger.info.call_args_list = []

        title = self.bc.fake.slug()
        body = self.bc.fake.slug()
        url = self.bc.fake.url()

        result = sync_single_issue(
            {"node_id": 1, "title": title, "body": body, "html_url": url}, freelancer=models1.freelancer
        )

        self.assertEqual(
            self.bc.database.list_of("freelance.Issue"),
            [
                issue_item({"node_id": str(1), "title": title, "body": body, "url": url}),
            ],
        )

        self.assertEqual(Logger.info.call_args_list, [])

    @patch("logging.Logger.info", MagicMock())
    def test_IssueWith_number(self):

        models1 = self.bc.database.create(freelancer=1)
        Logger.info.call_args_list = []

        title = self.bc.fake.slug()
        body = self.bc.fake.slug()
        url = self.bc.fake.url()
        number = random.randint(1, 10)

        result = sync_single_issue(
            {"node_id": 1, "title": title, "body": body, "html_url": url, "number": number},
            freelancer=models1.freelancer,
        )

        self.assertEqual(
            self.bc.database.list_of("freelance.Issue"),
            [
                issue_item({"node_id": str(1), "title": title, "body": body, "url": url, "github_number": number}),
            ],
        )

        self.assertEqual(Logger.info.call_args_list, [])

    @patch("logging.Logger.info", MagicMock())
    def test_resultSearch_isNotNone(self):

        models1 = self.bc.database.create(freelancer=1)
        Logger.info.call_args_list = []

        title = self.bc.fake.slug()
        body = self.bc.fake.slug()
        result = self.bc.fake.url()
        url = self.bc.fake.url()
        repository_url = "https://github.com/etolopez/apiv2/asdasd"

        res = sync_single_issue(
            {
                "node_id": 1,
                "title": title,
                "body": body,
                "result": result,
                "html_url": repository_url,
            },
            freelancer=models1.freelancer,
        )

        self.assertEqual(
            self.bc.database.list_of("freelance.Issue"),
            [
                issue_item(
                    {
                        "node_id": str(1),
                        "title": title,
                        "body": body,
                        "url": repository_url,
                        "repository_url": repository_url[:-7],
                    }
                ),
            ],
        )

        self.assertEqual(Logger.info.call_args_list, [])

    @patch("logging.Logger.info", MagicMock())
    def testing_hours(self):

        models1 = self.bc.database.create(freelancer=1)
        Logger.info.call_args_list = []

        title = self.bc.fake.slug()
        hours = random.random() * 50
        minutes = hours * 60
        body = f"<hrs>{hours}</hrs>"
        url = self.bc.fake.url()

        result = sync_single_issue(
            {
                "node_id": 1,
                "title": title,
                "body": body,
                "html_url": url,
            },
            freelancer=models1.freelancer,
        )

        self.assertEqual(
            self.bc.database.list_of("freelance.Issue"),
            [
                issue_item(
                    {
                        "node_id": str(1),
                        "title": title,
                        "body": body,
                        "url": url,
                        "duration_in_hours": hours,
                        "duration_in_minutes": minutes,
                    }
                ),
            ],
        )

        self.assertEqual(
            Logger.info.call_args_list,
            [call(f"Updating issue 1 (None) hrs with {hours}, found <hrs> tag on updated body")],
        )

    @patch("logging.Logger.info", MagicMock())
    def testing_different_hours(self):

        models1 = self.bc.database.create(freelancer=1)
        Logger.info.call_args_list = []

        title = self.bc.fake.slug()
        hours = random.random() * 50
        another = random.random() * 50
        minutes = hours * 60
        issue_body = f"<hrs>{another}</hrs>"
        comment_body = f"<hrs>{hours}</hrs> <status>comment</status>"
        url = self.bc.fake.url()

        result = sync_single_issue(
            {
                "node_id": 1,
                "title": title,
                "body": issue_body,
                "html_url": url,
            },
            freelancer=models1.freelancer,
            comment={"body": comment_body},
        )

        self.assertEqual(
            self.bc.database.list_of("freelance.Issue"),
            [
                issue_item(
                    {
                        "node_id": str(1),
                        "title": title,
                        "body": issue_body,
                        "url": url,
                        "duration_in_hours": hours,
                        "duration_in_minutes": minutes,
                        "status_message": "The status COMMENT is not valid",
                    }
                ),
            ],
        )

        self.assertEqual(
            Logger.info.call_args_list,
            [
                call(f"Updating issue 1 (None) hrs with {another}, found <hrs> tag on updated body"),
                call(f"Updating issue 1 (None) hrs with {hours}, found <hrs> tag on new comment"),
                call("The status COMMENT is not valid"),
            ],
        )

    @patch("logging.Logger.info", MagicMock())
    def testing_correct_status_with_hours(self):

        models1 = self.bc.database.create(freelancer=1)
        Logger.info.call_args_list = []

        status = random.choice(["IGNORED", "DRAFT", "TODO", "DOING", "DONE"])
        title = self.bc.fake.slug()
        hours = random.random() * 50
        another = random.random() * 50
        minutes = hours * 60
        issue_body = f"<hrs>{another}</hrs>"
        comment_body = f"<hrs>{hours}</hrs> <status>{status}</status>"
        url = self.bc.fake.url()

        result = sync_single_issue(
            {
                "node_id": 1,
                "title": title,
                "body": issue_body,
                "html_url": url,
            },
            freelancer=models1.freelancer,
            comment={"body": comment_body},
        )

        self.assertEqual(
            self.bc.database.list_of("freelance.Issue"),
            [
                issue_item(
                    {
                        "node_id": str(1),
                        "title": title,
                        "body": issue_body,
                        "url": url,
                        "duration_in_hours": hours,
                        "duration_in_minutes": minutes,
                        "status": status,
                    }
                ),
            ],
        )

        self.assertEqual(
            Logger.info.call_args_list,
            [
                call(f"Updating issue 1 (None) hrs with {another}, found <hrs> tag on updated body"),
                call(f"Updating issue 1 (None) hrs with {hours}, found <hrs> tag on new comment"),
                call(f"Updating issue 1 (None) status to {status} found <status> tag on new comment"),
            ],
        )

    @patch("logging.Logger.info", MagicMock())
    def testing_Assignee_FreelancerIsNone(self):

        with self.assertRaisesMessage(Exception, "There was no freelancer associated with this issue"):
            models1 = self.bc.database.create(freelancer=None)
            Logger.info.call_args_list = []

            status = random.choice(["IGNORED", "DRAFT", "TODO", "DOING", "DONE"])
            title = self.bc.fake.slug()
            hours = random.random() * 50
            another = random.random() * 50
            minutes = hours * 60
            assignees = random.random() * 50
            issue_body = f"<hrs>{another}</hrs>"
            comment_body = f"<hrs>{hours}</hrs> <status>{status}</status>"
            url = self.bc.fake.url()

            result = sync_single_issue(
                {
                    "node_id": 1,
                    "title": title,
                    "body": issue_body,
                    "html_url": url,
                },
                freelancer=None,
            )

            issue_item(
                {
                    "node_id": str(1),
                    "title": title,
                    "body": issue_body,
                    "url": url,
                    "assignees": assignees,
                    "duration_in_hours": hours,
                    "duration_in_minutes": minutes,
                    "status": status,
                }
            )

            self.assertEqual(Logger.info.call_args_list, [])

    @patch("logging.Logger.info", MagicMock())
    def testing_AssigneeID_FreelancerIsNone(self):

        models1 = self.bc.database.create(freelancer=None)
        Logger.info.call_args_list = []

        assignment_id = 3
        status = random.choice(["IGNORED", "DRAFT", "TODO", "DOING", "DONE"])
        title = self.bc.fake.slug()
        hours = random.random() * 50
        another = random.random() * 50
        minutes = hours * 60
        freelancer: None
        assignees = [{"id": assignment_id}]
        assigne = assignees[0]
        issue_body = f"<hrs>{another}</hrs>"
        comment_body = f"<hrs>{hours}</hrs> <status>{status}</status>"
        url = self.bc.fake.url()

        with self.assertRaisesMessage(
            Exception,
            f'Assigned github user: {assigne["id"]} is not a freelancer but is the main user associated to this issue',
        ):
            result = sync_single_issue(
                {
                    "node_id": 1,
                    "title": title,
                    "body": issue_body,
                    "html_url": url,
                    "assignees": assignees,
                },
                freelancer=None,
            )

            issue_item(
                {
                    "node_id": str(1),
                    "title": title,
                    "body": issue_body,
                    "url": url,
                    "assignees": assignees,
                    "freelancer": freelancer,
                    "duration_in_hours": hours,
                    "duration_in_minutes": minutes,
                    "status": status,
                }
            )

            self.assertEqual(Logger.info.call_args_list, [])
