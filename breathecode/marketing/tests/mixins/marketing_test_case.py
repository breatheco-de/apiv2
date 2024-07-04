"""
Collections of mixins used to login in authorize microservice
"""

import os
import re
from breathecode.authenticate.models import Token
from unittest.mock import call
from breathecode.notify.actions import get_template_content
from rest_framework.test import APITestCase
from breathecode.tests.mixins import (
    GenerateModelsMixin,
    CacheMixin,
    TokenMixin,
    GenerateQueriesMixin,
    DatetimeMixin,
    BreathecodeMixin,
)
from breathecode.feedback.actions import strings


class MarketingTestCase(
    APITestCase, GenerateModelsMixin, CacheMixin, TokenMixin, GenerateQueriesMixin, DatetimeMixin, BreathecodeMixin
):
    """MarketingTestCase with auth methods"""

    def tearDown(self):
        self.clear_cache()

    def setUp(self):
        self.maxDiff = None

        self.generate_queries()
        self.set_test_instance(self)

    def get_token_key(self, id=None):
        kwargs = {}
        if id:
            kwargs["id"] = id
        return Token.objects.filter(**kwargs).values_list("key", flat=True).first()

    # This function was moved here because i want to use it as one example to
    # test the email
    def check_email_contain_a_correct_token(self, lang, dicts, mock, model):
        token = self.get_token_key()
        question = dicts[0]["title"]
        link = f"https://nps.4geeks.com/{dicts[0]['id']}?token={token}"

        args_list = mock.call_args_list

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
        )

        self.assertEqual(
            args_list,
            [
                call(
                    "https://api.mailgun.net/v3/None/messages",
                    auth=("api", os.environ.get("MAILGUN_API_KEY", "")),
                    data={
                        "from": f"4Geeks <mailgun@{os.environ.get('MAILGUN_DOMAIN')}>",
                        "to": model["user"].email,
                        "subject": template["subject"],
                        "text": template["text"],
                        "html": template["html"],
                    },
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
                "The 4Geeks Team",
            },
        )
        self.assertToken(token)
        self.assertTrue(link in html)

    def check_old_breathecode_calls(self, mock, model, course=None):
        extras = {}

        if course:
            extras["field[2,0]"] = "asdasd"

        self.assertEqual(
            mock.call_args_list,
            [
                call(
                    "POST",
                    "https://old.hardcoded.breathecode.url/admin/api.php",
                    params=[
                        ("api_action", "contact_sync"),
                        ("api_key", model["active_campaign_academy"].ac_key),
                        ("api_output", "json"),
                    ],
                    data={
                        "email": "pokemon@potato.io",
                        "first_name": "Konan",
                        "last_name": "Amegakure",
                        "phone": "123123123",
                        "field[18,0]": model["academy"].slug,
                        **extras,
                    },
                ),
                call(
                    "POST",
                    "https://old.hardcoded.breathecode.url/api/3/contactAutomations",
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "Api-Token": model["active_campaign_academy"].ac_key,
                    },
                    json={"contactAutomation": {"contact": 1, "automation": model["automation"].acp_id}},
                ),
                call(
                    "POST",
                    "https://old.hardcoded.breathecode.url/api/3/contactTags",
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "Api-Token": model["active_campaign_academy"].ac_key,
                    },
                    json={"contactTag": {"contact": 1, "tag": model["tag"].acp_id}},
                ),
            ],
        )
