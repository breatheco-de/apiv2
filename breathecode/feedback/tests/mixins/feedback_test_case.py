"""
Collections of mixins used to login in authorize microservice
"""

import os
from unittest.mock import call

from rest_framework.test import APITestCase

from breathecode.authenticate.models import Token
from breathecode.notify.actions import get_template_content
from breathecode.tests.mixins import (
    BreathecodeMixin,
    CacheMixin,
    DatetimeMixin,
    GenerateModelsMixin,
    GenerateQueriesMixin,
    HeadersMixin,
    TokenMixin,
)

from ...actions import strings
from ...models import Answer


class FeedbackTestCase(
    APITestCase,
    GenerateModelsMixin,
    CacheMixin,
    TokenMixin,
    GenerateQueriesMixin,
    HeadersMixin,
    DatetimeMixin,
    BreathecodeMixin,
):
    """FeedbackTestCase with auth methods"""

    def tearDown(self):
        self.clear_cache()

    def setUp(self):
        self.generate_queries()
        self.set_test_instance(self)

    def get_token_key(self, id=None):
        kwargs = {}
        if id:
            kwargs["id"] = id
        return Token.objects.filter(**kwargs).values_list("key", flat=True).first()

    def remove_all_answer(self):
        Answer.objects.all().delete()

    def check_email_contain_a_correct_token(self, lang, dicts, mock, model):
        token = self.get_token_key()
        question = dicts[0]["title"]
        link = f"https://nps.4geeks.com/{dicts[0]['id']}?token={token}"

        args_list = mock.call_args_list
        academy = model.get("academy", None)

        template = get_template_content(
            "nps",
            {
                "QUESTION": question,
                "HIGHEST": dicts[0]["highest"],
                "LOWEST": dicts[0]["lowest"],
                "SUBJECT": question,
                "ANSWER_ID": dicts[0]["id"],
                "BUTTON": strings[lang]["button_label"],
                "LINK": link,
            },
            ["email"],
            academy=academy,
        )

        self.assertEqual(
            args_list,
            [
                call(
                    f'https://api.mailgun.net/v3/{os.environ.get("MAILGUN_DOMAIN")}/messages',
                    auth=("api", os.environ.get("MAILGUN_API_KEY", "")),
                    data={
                        "from": f"4Geeks <mailgun@{os.environ.get('MAILGUN_DOMAIN')}>",
                        "to": [model["user"].email],
                        "subject": template["subject"],
                        "text": template["text"],
                        "html": template["html"],
                    },
                    timeout=2,
                )
            ],
        )

        html = template["html"]
        del template["html"]
        self.assertEqual(
            template,
            {
                "SUBJECT": question,
                "subject": question,
                "text": "\n"
                "\n"
                "Please take 2 min to answer the following question:\n"
                "\n"
                f"{question}\n"
                "\n"
                "Click here to vote: "
                f"{link}"
                "\n"
                "\n"
                "\n"
                "\n"
                "The 4Geeks Team"
                "\n",
            },
        )
        self.assertToken(token)
        self.assertTrue(link in html)

    def check_slack_contain_a_correct_token(self, lang, dicts, mock, model, answer_id=1):
        token = self.get_token_key()
        slack_token = model["slack_team"].owner.credentialsslack.token
        slack_id = model["slack_user"].slack_id
        args_list = mock.call_args_list
        question = dicts[0]["title"]
        answer = strings[lang]["button_label"]

        expected = [
            call(
                method="POST",
                url="https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {slack_token}", "Content-type": "application/json"},
                params=None,
                json={
                    "channel": slack_id,
                    "private_metadata": "",
                    "blocks": [
                        {"type": "header", "text": {"type": "plain_text", "text": question, "emoji": True}},
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {"type": "plain_text", "text": answer, "emoji": True},
                                    "url": f"https://nps.4geeks.com/{answer_id}?token={token}",
                                }
                            ],
                        },
                    ],
                    "parse": "full",
                },
                timeout=10,
            )
        ]

        self.assertEqual(args_list, expected)
