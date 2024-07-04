"""
Test /answer/:id
"""

import os
from unittest.mock import MagicMock, call, patch
from breathecode.marketing.tasks import add_event_tags_to_student
from breathecode.tests.mocks.requests import apply_requests_get_mock, apply_requests_post_mock
from ..mixins import MarketingTestCase

GOOGLE_CLOUD_KEY = os.getenv("GOOGLE_CLOUD_KEY", None)
AC_HOST = "https://ac.ca"
AC_URL = f"{AC_HOST}/api/3/contacts"
AC_POST_URL = f"{AC_HOST}/api/3/contactTags"
AC_RESPONSE = {
    "contacts": [
        {
            "id": 1,
            "tag": "they-killed-kenny",
        },
    ]
}
AC_EMPTY_RESPONSE = {"contacts": []}
AC_POST_RESPONSE = {"contactTag": {}}
TASK_STARTED_MESSAGE = "Task add_event_tags_to_student started"
GET_CONTACT_BY_EMAIL_PATH = "breathecode.services.activecampaign.client.ActiveCampaign." "get_contact_by_email"

ADD_TAG_TO_CONTACT_PATH = "breathecode.services.activecampaign.client.ActiveCampaign." "add_tag_to_contact"

GET_CONTACT_BY_EMAIL_EXCEPTION = "Random exception in get_contact_by_email"
ADD_TAG_TO_CONTACT_EXCEPTION = "Random exception in add_tag_to_contact"
NEW_RELIC_LOG = "New Relic Python Agent (9.1.2)"


class AnswerIdTestSuite(MarketingTestCase):
    """
    🔽🔽🔽 Without optional arguments
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("requests.get", apply_requests_get_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch("requests.post", apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    @patch("breathecode.events.signals.event_saved", MagicMock())
    def test_add_event_tags_to_student__without_optional_arguments(self):
        import logging
        import requests

        add_event_tags_to_student.delay(1)

        self.assertEqual(logging.Logger.info.call_args_list, [call(TASK_STARTED_MESSAGE)])
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("Impossible to determine the user email", exc_info=True),
            ],
        )

        self.assertEqual(requests.get.call_args_list, [])
        self.assertEqual(requests.post.call_args_list, [])

    """
    🔽🔽🔽 Without Academy
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("requests.get", apply_requests_get_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch("requests.post", apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    @patch("breathecode.events.signals.event_saved", MagicMock())
    def test_add_event_tags_to_student__user_id_and_email(self):
        import logging
        import requests

        add_event_tags_to_student.delay(1, user_id=1, email="pokemon@potato.io")

        self.assertEqual(logging.Logger.info.call_args_list, [call(TASK_STARTED_MESSAGE)])
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("You can't provide the user_id and email together", exc_info=True),
            ],
        )

        self.assertEqual(requests.get.call_args_list, [])
        self.assertEqual(requests.post.call_args_list, [])

    """
    🔽🔽🔽 Without User
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("requests.get", apply_requests_get_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch("requests.post", apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    @patch("breathecode.events.signals.event_saved", MagicMock())
    def test_add_event_tags_to_student__without_user(self):
        import logging
        import requests

        add_event_tags_to_student.delay(1, user_id=1)

        self.assertEqual(logging.Logger.info.call_args_list, [call(TASK_STARTED_MESSAGE)])
        self.assertEqual(logging.Logger.error.call_args_list, [call("We can't get the user email", exc_info=True)])
        self.assertEqual(requests.get.call_args_list, [])
        self.assertEqual(requests.post.call_args_list, [])

    """
    🔽🔽🔽 Without Event
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("requests.get", apply_requests_get_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch("requests.post", apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    @patch("breathecode.events.signals.event_saved", MagicMock())
    def test_add_event_tags_to_student__without_event__with_user(self):
        import logging
        import requests

        self.generate_models(user=True)

        logging.Logger.info.call_args_list = []

        add_event_tags_to_student.delay(1, user_id=1)

        self.assertEqual(logging.Logger.info.call_args_list, [call(TASK_STARTED_MESSAGE)])
        self.assertEqual(logging.Logger.error.call_args_list, [call("Event 1 not found", exc_info=True)])
        self.assertEqual(requests.get.call_args_list, [])
        self.assertEqual(requests.post.call_args_list, [])

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("requests.get", apply_requests_get_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch("breathecode.events.signals.event_saved", MagicMock())
    @patch("requests.post", apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    @patch("breathecode.events.signals.event_saved", MagicMock())
    def test_add_event_tags_to_student__without_event__with_email(self):
        import logging
        import requests

        add_event_tags_to_student.delay(1, email="pokemon@potato.io")

        self.assertEqual(logging.Logger.info.call_args_list, [call(TASK_STARTED_MESSAGE)])
        self.assertEqual(logging.Logger.error.call_args_list, [call("Event 1 not found", exc_info=True)])
        self.assertEqual(requests.get.call_args_list, [])
        self.assertEqual(requests.post.call_args_list, [])

    """
    🔽🔽🔽 Without Academy
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("requests.get", apply_requests_get_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch("breathecode.events.signals.event_saved", MagicMock())
    @patch("requests.post", apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    @patch("breathecode.events.signals.event_saved", MagicMock())
    def test_add_event_tags_to_student__without_academy__with_user(self):
        import logging
        import requests

        self.generate_models(user=True, event=True)

        logging.Logger.info.call_args_list = []

        add_event_tags_to_student.delay(1, user_id=1)

        self.assertEqual(logging.Logger.info.call_args_list, [call(TASK_STARTED_MESSAGE)])
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("Impossible to determine the academy", exc_info=True),
            ],
        )

        self.assertEqual(requests.get.call_args_list, [])
        self.assertEqual(requests.post.call_args_list, [])

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("requests.get", apply_requests_get_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch("requests.post", apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    @patch("breathecode.events.signals.event_saved", MagicMock())
    def test_add_event_tags_to_student__without_academy__with_email(self):
        import logging
        import requests

        self.generate_models(event=True)

        logging.Logger.info.call_args_list = []

        add_event_tags_to_student.delay(1, email="pokemon@potato.io")

        self.assertEqual(logging.Logger.info.call_args_list, [call(TASK_STARTED_MESSAGE)])
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("Impossible to determine the academy", exc_info=True),
            ],
        )

        self.assertEqual(requests.get.call_args_list, [])
        self.assertEqual(requests.post.call_args_list, [])

    """
    🔽🔽🔽 Without ActiveCampaignAcademy
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("requests.get", apply_requests_get_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch("requests.post", apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    @patch("breathecode.events.signals.event_saved", MagicMock())
    def test_add_event_tags_to_student__without_active_campaign_academy__with_user(self):
        import logging
        import requests

        self.generate_models(user=True, event=True, academy=True)

        logging.Logger.info.call_args_list = []

        add_event_tags_to_student.delay(1, user_id=1)

        self.assertEqual(logging.Logger.info.call_args_list, [call(TASK_STARTED_MESSAGE)])
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("ActiveCampaign Academy 1 not found", exc_info=True),
            ],
        )

        self.assertEqual(requests.get.call_args_list, [])
        self.assertEqual(requests.post.call_args_list, [])

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("requests.get", apply_requests_get_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch("requests.post", apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    @patch("breathecode.events.signals.event_saved", MagicMock())
    def test_add_event_tags_to_student__without_active_campaign_academy__with_email(self):
        import logging
        import requests

        self.generate_models(event=True, academy=True)

        logging.Logger.info.call_args_list = []

        add_event_tags_to_student.delay(1, email="pokemon@potato.io")

        self.assertEqual(logging.Logger.info.call_args_list, [call(TASK_STARTED_MESSAGE)])
        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("ActiveCampaign Academy 1 not found", exc_info=True),
            ],
        )

        self.assertEqual(requests.get.call_args_list, [])
        self.assertEqual(requests.post.call_args_list, [])

    """
    🔽🔽🔽 Without Tag
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("requests.get", apply_requests_get_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch("requests.post", apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    @patch("breathecode.events.signals.event_saved", MagicMock())
    def test_add_event_tags_to_student__without_tags__with_user(self):
        import logging
        import requests

        self.generate_models(user=True, event=True, academy=True, active_campaign_academy=True)

        logging.Logger.info.call_args_list = []

        add_event_tags_to_student.delay(1, user_id=1)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call(TASK_STARTED_MESSAGE),
            ],
        )

        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("Tags not found", exc_info=True),
            ],
        )

        self.assertEqual(requests.get.call_args_list, [])
        self.assertEqual(requests.post.call_args_list, [])

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("requests.get", apply_requests_get_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch("requests.post", apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    @patch("breathecode.events.signals.event_saved", MagicMock())
    def test_add_event_tags_to_student__without_tags__with_email(self):
        import logging
        import requests

        self.generate_models(event=True, academy=True, active_campaign_academy=True)

        logging.Logger.info.call_args_list = []

        add_event_tags_to_student.delay(1, email="pokemon@potato.io")

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call(TASK_STARTED_MESSAGE),
            ],
        )

        self.assertEqual(
            logging.Logger.error.call_args_list,
            [
                call("Tags not found", exc_info=True),
            ],
        )

        self.assertEqual(requests.get.call_args_list, [])
        self.assertEqual(requests.post.call_args_list, [])

    """
    🔽🔽🔽 With a exception in ActiveCampaign.get_contact_by_email
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch(GET_CONTACT_BY_EMAIL_PATH, MagicMock(side_effect=Exception(GET_CONTACT_BY_EMAIL_EXCEPTION)))
    @patch("requests.get", apply_requests_get_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch("requests.post", apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    @patch("breathecode.events.signals.event_saved", MagicMock())
    def test_add_event_tags_to_student__exception_in_get_contact_by_email__with_user(self):
        import logging
        import requests

        tag_kwargs = {"slug": "they-killed-kenny"}
        event_kwargs = {"tags": "they-killed-kenny"}
        active_campaign_academy_kwargs = {"ac_url": AC_HOST}
        model = self.generate_models(
            user=True,
            event=True,
            academy=True,
            active_campaign_academy=True,
            tag=True,
            tag_kwargs=tag_kwargs,
            event_kwargs=event_kwargs,
            active_campaign_academy_kwargs=active_campaign_academy_kwargs,
        )

        logging.Logger.info.call_args_list = []

        logging.Logger.info.call_args_list = []

        add_event_tags_to_student.delay(1, user_id=1)

        self.assertEqual(logging.Logger.info.call_args_list, [call(TASK_STARTED_MESSAGE)])
        self.assertEqual(logging.Logger.error.call_args_list, [call(GET_CONTACT_BY_EMAIL_EXCEPTION, exc_info=True)])

        self.assertEqual(requests.get.call_args_list, [])
        self.assertEqual(requests.post.call_args_list, [])

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch(GET_CONTACT_BY_EMAIL_PATH, MagicMock(side_effect=Exception(GET_CONTACT_BY_EMAIL_EXCEPTION)))
    @patch("requests.get", apply_requests_get_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch("requests.post", apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    @patch("breathecode.events.signals.event_saved", MagicMock())
    def test_add_event_tags_to_student__exception_in_get_contact_by_email__with_email(self):
        import logging
        import requests

        tag_kwargs = {"slug": "they-killed-kenny"}
        event_kwargs = {"tags": "they-killed-kenny"}
        active_campaign_academy_kwargs = {"ac_url": AC_HOST}
        model = self.generate_models(
            event=True,
            academy=True,
            active_campaign_academy=True,
            tag=True,
            tag_kwargs=tag_kwargs,
            event_kwargs=event_kwargs,
            active_campaign_academy_kwargs=active_campaign_academy_kwargs,
        )

        logging.Logger.info.call_args_list = []

        add_event_tags_to_student.delay(1, email="pokemon@potato.io")

        self.assertEqual(logging.Logger.info.call_args_list, [call(TASK_STARTED_MESSAGE)])
        self.assertEqual(logging.Logger.error.call_args_list, [call(GET_CONTACT_BY_EMAIL_EXCEPTION, exc_info=True)])

        self.assertEqual(requests.get.call_args_list, [])
        self.assertEqual(requests.post.call_args_list, [])

    """
    🔽🔽🔽 With a exception in ActiveCampaign.add_tag_to_contact
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch(ADD_TAG_TO_CONTACT_PATH, MagicMock(side_effect=Exception(ADD_TAG_TO_CONTACT_EXCEPTION)))
    @patch("requests.get", apply_requests_get_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch("requests.post", apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    @patch("breathecode.events.signals.event_saved", MagicMock())
    def test_add_event_tags_to_student__exception_in_add_tag_to_contact__with_user(self):
        import logging
        import requests

        tag_kwargs = {"slug": "they-killed-kenny"}
        event_kwargs = {"tags": "they-killed-kenny"}
        active_campaign_academy_kwargs = {"ac_url": AC_HOST}
        model = self.generate_models(
            user=True,
            event=True,
            academy=True,
            active_campaign_academy=True,
            tag=True,
            tag_kwargs=tag_kwargs,
            event_kwargs=event_kwargs,
            active_campaign_academy_kwargs=active_campaign_academy_kwargs,
        )

        logging.Logger.info.call_args_list = []

        add_event_tags_to_student.delay(1, user_id=1)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call(TASK_STARTED_MESSAGE),
                call("Adding tag 1 to acp contact 1"),
            ],
        )

        self.assertEqual(logging.Logger.error.call_args_list, [call(ADD_TAG_TO_CONTACT_EXCEPTION, exc_info=True)])
        self.assertEqual(
            requests.get.call_args_list,
            [
                call(
                    "https://ac.ca/api/3/contacts",
                    headers={"Api-Token": model.active_campaign_academy.ac_key},
                    params={"email": model.user.email},
                    timeout=2,
                ),
            ],
        )

        self.assertEqual(requests.post.call_args_list, [])

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch(ADD_TAG_TO_CONTACT_PATH, MagicMock(side_effect=Exception(ADD_TAG_TO_CONTACT_EXCEPTION)))
    @patch("requests.get", apply_requests_get_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch("requests.post", apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    @patch("breathecode.events.signals.event_saved", MagicMock())
    def test_add_event_tags_to_student__exception_in_add_tag_to_contact__with_email(self):
        import logging
        import requests

        tag_kwargs = {"slug": "they-killed-kenny"}
        event_kwargs = {"tags": "they-killed-kenny"}
        active_campaign_academy_kwargs = {"ac_url": AC_HOST}
        model = self.generate_models(
            event=True,
            academy=True,
            active_campaign_academy=True,
            tag=True,
            tag_kwargs=tag_kwargs,
            event_kwargs=event_kwargs,
            active_campaign_academy_kwargs=active_campaign_academy_kwargs,
        )

        logging.Logger.info.call_args_list = []

        add_event_tags_to_student.delay(1, email="pokemon@potato.io")

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call(TASK_STARTED_MESSAGE),
                call("Adding tag 1 to acp contact 1"),
            ],
        )

        self.assertEqual(logging.Logger.error.call_args_list, [call(ADD_TAG_TO_CONTACT_EXCEPTION, exc_info=True)])
        self.assertEqual(
            requests.get.call_args_list,
            [
                call(
                    "https://ac.ca/api/3/contacts",
                    headers={"Api-Token": model.active_campaign_academy.ac_key},
                    params={"email": "pokemon@potato.io"},
                    timeout=2,
                ),
            ],
        )

        self.assertEqual(requests.post.call_args_list, [])

    """
    🔽🔽🔽 With one Tag
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("requests.get", apply_requests_get_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch("requests.post", apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    @patch("breathecode.events.signals.event_saved", MagicMock())
    def test_add_event_tags_to_student__with_one_tag__with_user(self):
        import logging
        import requests

        tag_kwargs = {"slug": "they-killed-kenny"}
        event_kwargs = {"tags": "they-killed-kenny"}
        active_campaign_academy_kwargs = {"ac_url": AC_HOST}
        model = self.generate_models(
            user=True,
            event=True,
            academy=True,
            active_campaign_academy=True,
            tag=True,
            tag_kwargs=tag_kwargs,
            event_kwargs=event_kwargs,
            active_campaign_academy_kwargs=active_campaign_academy_kwargs,
        )

        logging.Logger.info.call_args_list = []

        add_event_tags_to_student.delay(1, user_id=1)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call(TASK_STARTED_MESSAGE),
                call("Adding tag 1 to acp contact 1"),
            ],
        )

        self.assertEqual(logging.Logger.error.call_args_list, [])
        self.assertEqual(
            requests.get.call_args_list,
            [
                call(
                    "https://ac.ca/api/3/contacts",
                    headers={"Api-Token": model.active_campaign_academy.ac_key},
                    params={"email": model.user.email},
                    timeout=2,
                ),
            ],
        )

        self.assertEqual(
            requests.post.call_args_list,
            [
                call(
                    "https://ac.ca/api/3/contactTags",
                    headers={
                        "Api-Token": model.active_campaign_academy.ac_key,
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json={"contactTag": {"contact": 1, "tag": model.tag.acp_id}},
                    timeout=2,
                ),
            ],
        )

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("requests.get", apply_requests_get_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch("requests.post", apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    @patch("breathecode.events.signals.event_saved", MagicMock())
    def test_add_event_tags_to_student__with_one_tag__with_email(self):
        import logging
        import requests

        tag_kwargs = {"slug": "they-killed-kenny"}
        event_kwargs = {"tags": "they-killed-kenny"}
        active_campaign_academy_kwargs = {"ac_url": AC_HOST}
        model = self.generate_models(
            event=True,
            academy=True,
            active_campaign_academy=True,
            tag=True,
            tag_kwargs=tag_kwargs,
            event_kwargs=event_kwargs,
            active_campaign_academy_kwargs=active_campaign_academy_kwargs,
        )

        logging.Logger.info.call_args_list = []

        add_event_tags_to_student.delay(1, email="pokemon@potato.io")

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call(TASK_STARTED_MESSAGE),
                call("Adding tag 1 to acp contact 1"),
            ],
        )

        self.assertEqual(logging.Logger.error.call_args_list, [])
        self.assertEqual(
            requests.get.call_args_list,
            [
                call(
                    "https://ac.ca/api/3/contacts",
                    headers={"Api-Token": model.active_campaign_academy.ac_key},
                    params={"email": "pokemon@potato.io"},
                    timeout=2,
                ),
            ],
        )

        self.assertEqual(
            requests.post.call_args_list,
            [
                call(
                    "https://ac.ca/api/3/contactTags",
                    headers={
                        "Api-Token": model.active_campaign_academy.ac_key,
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json={"contactTag": {"contact": 1, "tag": model.tag.acp_id}},
                    timeout=2,
                ),
            ],
        )

    """
    🔽🔽🔽 With two Tags
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("requests.get", apply_requests_get_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch("requests.post", apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    @patch("breathecode.events.signals.event_saved", MagicMock())
    def test_add_event_tags_to_student__with_two_tags__with_user(self):
        import logging
        import requests

        event_kwargs = {"tags": "they-killed-kenny1,they-killed-kenny2"}
        active_campaign_academy_kwargs = {"ac_url": AC_HOST}
        base = self.generate_models(
            user=True,
            event=True,
            academy=True,
            active_campaign_academy=True,
            event_kwargs=event_kwargs,
            active_campaign_academy_kwargs=active_campaign_academy_kwargs,
        )

        tag_kwargs = {"slug": "they-killed-kenny1"}
        model1 = self.generate_models(tag=True, tag_kwargs=tag_kwargs, models=base)

        tag_kwargs = {"slug": "they-killed-kenny2"}
        model2 = self.generate_models(tag=True, tag_kwargs=tag_kwargs, models=base)

        logging.Logger.info.call_args_list = []

        add_event_tags_to_student.delay(1, user_id=1)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call(TASK_STARTED_MESSAGE),
                call("Adding tag 1 to acp contact 1"),
                call("Adding tag 2 to acp contact 1"),
            ],
        )

        self.assertEqual(logging.Logger.error.call_args_list, [])
        self.assertEqual(
            requests.get.call_args_list,
            [
                call(
                    "https://ac.ca/api/3/contacts",
                    headers={"Api-Token": model1.active_campaign_academy.ac_key},
                    params={"email": model1.user.email},
                    timeout=2,
                ),
            ],
        )

        self.assertEqual(
            requests.post.call_args_list,
            [
                call(
                    "https://ac.ca/api/3/contactTags",
                    headers={
                        "Api-Token": model1.active_campaign_academy.ac_key,
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json={"contactTag": {"contact": 1, "tag": model1.tag.acp_id}},
                    timeout=2,
                ),
                call(
                    "https://ac.ca/api/3/contactTags",
                    headers={
                        "Api-Token": model1.active_campaign_academy.ac_key,
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json={"contactTag": {"contact": 1, "tag": model2.tag.acp_id}},
                    timeout=2,
                ),
            ],
        )

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("requests.get", apply_requests_get_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch("requests.post", apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    @patch("breathecode.events.signals.event_saved", MagicMock())
    def test_add_event_tags_to_student__with_two_tags__with_email(self):
        import logging
        import requests

        event_kwargs = {"tags": "they-killed-kenny1,they-killed-kenny2"}
        active_campaign_academy_kwargs = {"ac_url": AC_HOST}
        base = self.generate_models(
            event=True,
            academy=True,
            active_campaign_academy=True,
            event_kwargs=event_kwargs,
            active_campaign_academy_kwargs=active_campaign_academy_kwargs,
        )

        tag_kwargs = {"slug": "they-killed-kenny1"}
        model1 = self.generate_models(tag=True, tag_kwargs=tag_kwargs, models=base)

        tag_kwargs = {"slug": "they-killed-kenny2"}
        model2 = self.generate_models(tag=True, tag_kwargs=tag_kwargs, models=base)

        logging.Logger.info.call_args_list = []

        add_event_tags_to_student.delay(1, email="pokemon@potato.io")

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call(TASK_STARTED_MESSAGE),
                call("Adding tag 1 to acp contact 1"),
                call("Adding tag 2 to acp contact 1"),
            ],
        )

        self.assertEqual(logging.Logger.error.call_args_list, [])
        self.assertEqual(
            requests.get.call_args_list,
            [
                call(
                    "https://ac.ca/api/3/contacts",
                    headers={"Api-Token": model1.active_campaign_academy.ac_key},
                    params={"email": "pokemon@potato.io"},
                    timeout=2,
                ),
            ],
        )

        self.assertEqual(
            requests.post.call_args_list,
            [
                call(
                    "https://ac.ca/api/3/contactTags",
                    headers={
                        "Api-Token": model1.active_campaign_academy.ac_key,
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json={"contactTag": {"contact": 1, "tag": model1.tag.acp_id}},
                    timeout=2,
                ),
                call(
                    "https://ac.ca/api/3/contactTags",
                    headers={
                        "Api-Token": model1.active_campaign_academy.ac_key,
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json={"contactTag": {"contact": 1, "tag": model2.tag.acp_id}},
                    timeout=2,
                ),
            ],
        )

    """
    🔽🔽🔽 With two Tags, a with event name and the other from the tags attr
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("requests.get", apply_requests_get_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch("requests.post", apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    @patch("breathecode.events.signals.event_saved", MagicMock())
    def test_add_event_tags_to_student__with_two_tags__event_slug_math_with_tag__with_user(self):
        import logging
        import requests

        active_campaign_academy_kwargs = {"ac_url": AC_HOST}
        event_kwargs = {
            "slug": "they-killed-kenny1",
            "tags": "they-killed-kenny2",
        }

        base = self.generate_models(
            user=True,
            event=True,
            academy=True,
            active_campaign_academy=True,
            event_kwargs=event_kwargs,
            active_campaign_academy_kwargs=active_campaign_academy_kwargs,
        )

        tag_kwargs = {"slug": "event-they-killed-kenny1"}
        model1 = self.generate_models(tag=True, tag_kwargs=tag_kwargs, models=base)
        tag_kwargs = {"slug": "they-killed-kenny2"}
        model2 = self.generate_models(tag=True, tag_kwargs=tag_kwargs, models=base)

        logging.Logger.info.call_args_list = []

        add_event_tags_to_student.delay(1, user_id=1)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call(TASK_STARTED_MESSAGE),
                call("Adding tag 1 to acp contact 1"),
                call("Adding tag 2 to acp contact 1"),
            ],
        )

        self.assertEqual(logging.Logger.error.call_args_list, [])
        self.assertEqual(
            requests.get.call_args_list,
            [
                call(
                    "https://ac.ca/api/3/contacts",
                    headers={"Api-Token": model1.active_campaign_academy.ac_key},
                    params={"email": model1.user.email},
                    timeout=2,
                ),
            ],
        )

        self.assertEqual(
            requests.post.call_args_list,
            [
                call(
                    "https://ac.ca/api/3/contactTags",
                    headers={
                        "Api-Token": model1.active_campaign_academy.ac_key,
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json={"contactTag": {"contact": 1, "tag": model1.tag.acp_id}},
                    timeout=2,
                ),
                call(
                    "https://ac.ca/api/3/contactTags",
                    headers={
                        "Api-Token": model1.active_campaign_academy.ac_key,
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json={"contactTag": {"contact": 1, "tag": model2.tag.acp_id}},
                    timeout=2,
                ),
            ],
        )

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("requests.get", apply_requests_get_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch("requests.post", apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    @patch("breathecode.events.signals.event_saved", MagicMock())
    def test_add_event_tags_to_student__with_two_tags__event_slug_math_with_tag__with_email(self):
        import logging
        import requests

        active_campaign_academy_kwargs = {"ac_url": AC_HOST}
        event_kwargs = {
            "slug": "they-killed-kenny1",
            "tags": "they-killed-kenny2",
        }

        base = self.generate_models(
            event=True,
            academy=True,
            active_campaign_academy=True,
            event_kwargs=event_kwargs,
            active_campaign_academy_kwargs=active_campaign_academy_kwargs,
        )

        tag_kwargs = {"slug": "event-they-killed-kenny1"}
        model1 = self.generate_models(tag=True, tag_kwargs=tag_kwargs, models=base)
        tag_kwargs = {"slug": "they-killed-kenny2"}
        model2 = self.generate_models(tag=True, tag_kwargs=tag_kwargs, models=base)

        logging.Logger.info.call_args_list = []

        add_event_tags_to_student.delay(1, email="pokemon@potato.io")

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call(TASK_STARTED_MESSAGE),
                call("Adding tag 1 to acp contact 1"),
                call("Adding tag 2 to acp contact 1"),
            ],
        )

        self.assertEqual(logging.Logger.error.call_args_list, [])
        self.assertEqual(
            requests.get.call_args_list,
            [
                call(
                    "https://ac.ca/api/3/contacts",
                    headers={"Api-Token": model1.active_campaign_academy.ac_key},
                    params={"email": "pokemon@potato.io"},
                    timeout=2,
                ),
            ],
        )

        self.assertEqual(
            requests.post.call_args_list,
            [
                call(
                    "https://ac.ca/api/3/contactTags",
                    headers={
                        "Api-Token": model1.active_campaign_academy.ac_key,
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json={"contactTag": {"contact": 1, "tag": model1.tag.acp_id}},
                    timeout=2,
                ),
                call(
                    "https://ac.ca/api/3/contactTags",
                    headers={
                        "Api-Token": model1.active_campaign_academy.ac_key,
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json={"contactTag": {"contact": 1, "tag": model2.tag.acp_id}},
                    timeout=2,
                ),
            ],
        )

    """
    🔽🔽🔽 With three Tags, a with event name and the other from the tags attr
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("requests.get", apply_requests_get_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch("requests.post", apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    @patch("breathecode.events.signals.event_saved", MagicMock())
    def test_add_event_tags_to_student__with_three_tags__event_slug_math_with_tag__with_user(self):
        import logging
        import requests

        active_campaign_academy_kwargs = {"ac_url": AC_HOST}
        event_kwargs = {
            "slug": "they-killed-kenny1",
            "tags": "they-killed-kenny2,they-killed-kenny3",
        }

        base = self.generate_models(
            user=True,
            event=True,
            academy=True,
            active_campaign_academy=True,
            event_kwargs=event_kwargs,
            active_campaign_academy_kwargs=active_campaign_academy_kwargs,
        )

        tag_kwargs = {"slug": "event-they-killed-kenny1"}
        model1 = self.generate_models(tag=True, tag_kwargs=tag_kwargs, models=base)

        tag_kwargs = {"slug": "they-killed-kenny2"}
        model2 = self.generate_models(tag=True, tag_kwargs=tag_kwargs, models=base)

        tag_kwargs = {"slug": "they-killed-kenny3"}
        model3 = self.generate_models(tag=True, tag_kwargs=tag_kwargs, models=base)

        logging.Logger.info.call_args_list = []

        add_event_tags_to_student.delay(1, user_id=1)

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call(TASK_STARTED_MESSAGE),
                call("Adding tag 1 to acp contact 1"),
                call("Adding tag 2 to acp contact 1"),
                call("Adding tag 3 to acp contact 1"),
            ],
        )

        self.assertEqual(logging.Logger.error.call_args_list, [])
        self.assertEqual(
            requests.get.call_args_list,
            [
                call(
                    "https://ac.ca/api/3/contacts",
                    headers={"Api-Token": model1.active_campaign_academy.ac_key},
                    params={"email": model1.user.email},
                    timeout=2,
                ),
            ],
        )

        self.assertEqual(
            requests.post.call_args_list,
            [
                call(
                    "https://ac.ca/api/3/contactTags",
                    headers={
                        "Api-Token": model1.active_campaign_academy.ac_key,
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json={"contactTag": {"contact": 1, "tag": model1.tag.acp_id}},
                    timeout=2,
                ),
                call(
                    "https://ac.ca/api/3/contactTags",
                    headers={
                        "Api-Token": model1.active_campaign_academy.ac_key,
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json={"contactTag": {"contact": 1, "tag": model2.tag.acp_id}},
                    timeout=2,
                ),
                call(
                    "https://ac.ca/api/3/contactTags",
                    headers={
                        "Api-Token": model1.active_campaign_academy.ac_key,
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json={"contactTag": {"contact": 1, "tag": model3.tag.acp_id}},
                    timeout=2,
                ),
            ],
        )

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("requests.get", apply_requests_get_mock([(200, AC_URL, AC_RESPONSE)]))
    @patch("requests.post", apply_requests_post_mock([(201, AC_POST_URL, AC_POST_RESPONSE)]))
    @patch("breathecode.events.signals.event_saved", MagicMock())
    def test_add_event_tags_to_student__with_three_tags__event_slug_math_with_tag__with_email(self):
        import logging
        import requests

        active_campaign_academy_kwargs = {"ac_url": AC_HOST}
        event_kwargs = {
            "slug": "they-killed-kenny1",
            "tags": "they-killed-kenny2,they-killed-kenny3",
        }

        base = self.generate_models(
            event=True,
            academy=True,
            active_campaign_academy=True,
            event_kwargs=event_kwargs,
            active_campaign_academy_kwargs=active_campaign_academy_kwargs,
        )

        tag_kwargs = {"slug": "event-they-killed-kenny1"}
        model1 = self.generate_models(tag=True, tag_kwargs=tag_kwargs, models=base)

        tag_kwargs = {"slug": "they-killed-kenny2"}
        model2 = self.generate_models(tag=True, tag_kwargs=tag_kwargs, models=base)

        tag_kwargs = {"slug": "they-killed-kenny3"}
        model3 = self.generate_models(tag=True, tag_kwargs=tag_kwargs, models=base)

        logging.Logger.info.call_args_list = []

        add_event_tags_to_student.delay(1, email="pokemon@potato.io")

        self.assertEqual(
            logging.Logger.info.call_args_list,
            [
                call(TASK_STARTED_MESSAGE),
                call("Adding tag 1 to acp contact 1"),
                call("Adding tag 2 to acp contact 1"),
                call("Adding tag 3 to acp contact 1"),
            ],
        )

        self.assertEqual(logging.Logger.error.call_args_list, [])
        self.assertEqual(
            requests.get.call_args_list,
            [
                call(
                    "https://ac.ca/api/3/contacts",
                    headers={"Api-Token": model1.active_campaign_academy.ac_key},
                    params={"email": "pokemon@potato.io"},
                    timeout=2,
                ),
            ],
        )

        self.assertEqual(
            requests.post.call_args_list,
            [
                call(
                    "https://ac.ca/api/3/contactTags",
                    headers={
                        "Api-Token": model1.active_campaign_academy.ac_key,
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json={"contactTag": {"contact": 1, "tag": model1.tag.acp_id}},
                    timeout=2,
                ),
                call(
                    "https://ac.ca/api/3/contactTags",
                    headers={
                        "Api-Token": model1.active_campaign_academy.ac_key,
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json={"contactTag": {"contact": 1, "tag": model2.tag.acp_id}},
                    timeout=2,
                ),
                call(
                    "https://ac.ca/api/3/contactTags",
                    headers={
                        "Api-Token": model1.active_campaign_academy.ac_key,
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json={"contactTag": {"contact": 1, "tag": model3.tag.acp_id}},
                    timeout=2,
                ),
            ],
        )
