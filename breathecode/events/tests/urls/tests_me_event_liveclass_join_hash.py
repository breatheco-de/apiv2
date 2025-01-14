import random
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

import pytest
from django.template import loader
from django.urls.base import reverse_lazy
from django.utils import timezone

from breathecode.events import tasks as tasks_events
from breathecode.events.caches import EventCache
from breathecode.payments import tasks

from ..mixins.new_events_tests_case import EventTestCase

UTC_NOW = timezone.now()


@pytest.fixture(autouse=True)
def setup(db):
    yield


def consumption_session(live_class, cohort_set, user, consumable, data={}):
    return {
        "consumable_id": consumable.id,
        "duration": timedelta(),
        "operation_code": "default",
        "eta": ...,
        "how_many": 1.0,
        "id": 0,
        "path": "payments.CohortSet",
        "related_id": cohort_set.id,
        "related_slug": cohort_set.slug,
        "request": {
            "args": [],
            "headers": {"academy": None},
            "kwargs": {
                "hash": live_class.hash,
            },
            "user": user.id,
        },
        "status": "PENDING",
        "user_id": user.id,
        "was_discounted": False,
        **data,
    }


# IMPORTANT: the loader.render_to_string in a function is inside of function render
def render_message(message, data={}):
    request = None
    context = {"MESSAGE": message, "BUTTON": None, "BUTTON_TARGET": "_blank", "LINK": None, **data}

    return loader.render_to_string("message.html", context, request)


def serializer(live_class):
    return {
        "id": live_class.id,
        "starting_at": live_class.starting_at,
        "ending_at": live_class.ending_at,
        "live_stream_url": live_class.cohort_time_slot.cohort.online_meeting_url,
        "title": live_class.cohort_time_slot.cohort.name,
    }


# IMPORTANT: the loader.render_to_string in a function is inside of function render
def render_countdown(live_class, token, academy=None):
    request = None
    context = {
        "event": serializer(live_class),
        "token": token.key,
    }

    if academy:
        context["COMPANY_INFO_EMAIL"] = academy.feedback_email
        context["COMPANY_LEGAL_NAME"] = academy.legal_name or academy.name
        context["COMPANY_LOGO"] = academy.logo_url
        context["COMPANY_NAME"] = academy.name

    return loader.render_to_string("countdown.html", context, request)


class AcademyEventTestSuite(EventTestCase):
    cache = EventCache()

    # When: no auth
    # Then: return 401
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_no_auth(self):

        url = reverse_lazy("events:me_event_liveclass_join_hash", kwargs={"hash": "potato"})

        response = self.client.get(url)

        url_hash = self.bc.format.to_base64("/v1/events/me/event/liveclass/join/potato")
        content = self.bc.format.from_bytes(response.content)
        expected = ""

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"/v1/auth/view/login?attempt=1&url={url_hash}")
        self.bc.check.calls(tasks.end_the_consumption_session.apply_async.call_args_list, [])

    # When: no consumables
    # Then: return 402
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_no_consumables(self):
        model = self.bc.database.create(user=1, token=1)
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = reverse_lazy("events:me_event_liveclass_join_hash", kwargs={"hash": "potato"}) + f"?{querystring}"

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_message("not-found")

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 404)

        self.assertEqual(self.bc.database.list_of("events.LiveClass"), [])
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])
        self.bc.check.calls(tasks.end_the_consumption_session.apply_async.call_args_list, [])

    # Given: no Consumable and LiveClass, User have Group and Permission
    # When: Feature flag set to False
    # Then: return 404
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_no_consumables__bypass_with_feature_flag__live_class_not_found(self):
        service = {"consumer": "LIVE_CLASS_JOIN"}
        model = self.bc.database.create(user=1, group=1, service=service, token=1)
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = reverse_lazy("events:me_event_liveclass_join_hash", kwargs={"hash": "potato"}) + f"?{querystring}"

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_message("not-found")

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 404)

        self.assertEqual(self.bc.database.list_of("events.LiveClass"), [])
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])
        self.bc.check.calls(tasks.end_the_consumption_session.apply_async.call_args_list, [])

    # Given: no Consumable, with LiveClass, CohortUser, User have Group and Permission
    # When: Feature flag set to False, right hash and cohort.live_class_join not set
    # Then: return 400
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_no_consumables__bypass_with_feature_flag__with_live_class__cohort_without_url(self):
        service = {"consumer": "LIVE_CLASS_JOIN"}
        delta = timedelta(seconds=random.randint(1, 1000))
        live_class = {"starting_at": UTC_NOW - delta, "ending_at": UTC_NOW + delta}
        model = self.bc.database.create(user=1, group=1, service=service, live_class=live_class, cohort_user=1, token=1)
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = (
            reverse_lazy("events:me_event_liveclass_join_hash", kwargs={"hash": model.live_class.hash})
            + f"?{querystring}"
        )

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_message("cohort-online-meeting-url-not-found")

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            self.bc.database.list_of("events.LiveClass"),
            [
                self.bc.format.to_dict(model.live_class),
            ],
        )
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])
        self.bc.check.calls(tasks.end_the_consumption_session.apply_async.call_args_list, [])

    # Given: no Consumable, with LiveClass, CohortUser, User have Group and Permission
    # When: Feature flag set to False, right hash and cohort.live_class_join set
    # Then: return 302 to cohort.online_meeting_url
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_no_consumables__bypass_with_feature_flag__with_live_class__cohort_with_url(self):
        service = {"consumer": "LIVE_CLASS_JOIN"}
        online_meeting_url = self.bc.fake.url()
        cohort = {"online_meeting_url": online_meeting_url}
        delta = timedelta(seconds=random.randint(1, 1000))
        live_class = {"starting_at": UTC_NOW - delta, "ending_at": UTC_NOW + delta}
        model = self.bc.database.create(
            user=1, group=1, service=service, live_class=live_class, cohort_user=1, cohort=cohort, token=1
        )
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = (
            reverse_lazy("events:me_event_liveclass_join_hash", kwargs={"hash": model.live_class.hash})
            + f"?{querystring}"
        )

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = ""

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, online_meeting_url)

        self.assertEqual(
            self.bc.database.list_of("events.LiveClass"),
            [
                self.bc.format.to_dict(model.live_class),
            ],
        )
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])
        self.bc.check.calls(tasks.end_the_consumption_session.apply_async.call_args_list, [])

    # Given: no Consumable and LiveClass, User have Group and Permission
    # When: Feature flag set to True
    # Then: return 404
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_no_consumables__it_try_to_consume__live_class_not_found(self):
        service = {"consumer": "LIVE_CLASS_JOIN"}
        model = self.bc.database.create(user=1, group=1, service=service, token=1)
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = reverse_lazy("events:me_event_liveclass_join_hash", kwargs={"hash": "potato"}) + f"?{querystring}"

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_message("not-found")

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 404)

        self.assertEqual(self.bc.database.list_of("events.LiveClass"), [])
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])
        self.bc.check.calls(tasks.end_the_consumption_session.apply_async.call_args_list, [])

    # Given: no Consumable with LiveClass, User have Group and Permission
    # When: Feature flag set to True and cohort.live_class_join not set
    # Then: return 400
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_no_consumables__it_try_to_consume__with_live_class__cohort_without_url(self):
        service = {"consumer": "LIVE_CLASS_JOIN"}
        delta = timedelta(seconds=random.randint(1, 1000))
        live_class = {"starting_at": UTC_NOW - delta, "ending_at": UTC_NOW + delta}
        model = self.bc.database.create(
            user=1, group=1, service=service, live_class=live_class, cohort_user=1, cohort=1, token=1
        )
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = (
            reverse_lazy("events:me_event_liveclass_join_hash", kwargs={"hash": model.live_class.hash})
            + f"?{querystring}"
        )

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_message("cohort-online-meeting-url-not-found")

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            self.bc.database.list_of("events.LiveClass"),
            [
                self.bc.format.to_dict(model.live_class),
            ],
        )
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])
        self.bc.check.calls(tasks.end_the_consumption_session.apply_async.call_args_list, [])

    # Given: no Consumable with LiveClass, User have Group and Permission
    # When: Feature flag set to True and cohort.live_class_join set
    # Then: return 402
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_no_consumables__it_try_to_consume__with_live_class__cohort_with_url(self):
        service = {"consumer": "LIVE_CLASS_JOIN"}
        online_meeting_url = self.bc.fake.url()
        cohort = {"online_meeting_url": online_meeting_url, "available_as_saas": True}
        delta = timedelta(seconds=random.randint(1, 1000))
        live_class = {"starting_at": UTC_NOW - delta, "ending_at": UTC_NOW + delta}
        model = self.bc.database.create(
            user=1, group=1, service=service, live_class=live_class, cohort_user=1, cohort=cohort, token=1
        )
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = (
            reverse_lazy("events:me_event_liveclass_join_hash", kwargs={"hash": model.live_class.hash})
            + f"?{querystring}"
        )

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        template_data = {}

        template_data["GO_BACK"] = "Go back to Dashboard"
        template_data["URL_BACK"] = "https://4geeks.com/choose-program"
        expected = render_message("with-consumer-not-enough-consumables", data=template_data)

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 402)

        self.assertEqual(
            self.bc.database.list_of("events.LiveClass"),
            [
                self.bc.format.to_dict(model.live_class),
            ],
        )
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])
        self.bc.check.calls(tasks.end_the_consumption_session.apply_async.call_args_list, [])

    # Given: with Consumable, LiveClass, User have Group and Permission
    # When: Feature flag set to True, class end in the past and cohort.live_class_join set
    # Then: return 200 and create a ConsumptionSession
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_with_consumable__it_try_to_consume__with_live_class__in_the_past(self):
        service = {"consumer": "LIVE_CLASS_JOIN"}
        online_meeting_url = self.bc.fake.url()
        cohort = {"online_meeting_url": online_meeting_url}
        delta = timedelta(seconds=random.randint(1, 1000))
        live_class = {"starting_at": UTC_NOW - delta, "ending_at": UTC_NOW - delta}
        model = self.bc.database.create(
            user=1, group=1, service=service, live_class=live_class, cohort_user=1, consumable=1, cohort=cohort, token=1
        )
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = (
            reverse_lazy("events:me_event_liveclass_join_hash", kwargs={"hash": model.live_class.hash})
            + f"?{querystring}"
        )

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_message("class-has-ended")

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            self.bc.database.list_of("events.LiveClass"),
            [
                self.bc.format.to_dict(model.live_class),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            [
                self.bc.format.to_dict(model.consumable),
            ],
        )

        self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])
        self.bc.check.calls(tasks.end_the_consumption_session.apply_async.call_args_list, [])

    # Given: with Consumable, LiveClass, User have Group and Permission
    # When: Feature flag set to True and class end in the future
    # Then: return 200 and create a ConsumptionSession
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_with_consumable__it_try_to_consume__with_live_class__in_the_future(self):
        service = {"consumer": "LIVE_CLASS_JOIN"}
        online_meeting_url = self.bc.fake.url()
        cohort = {"online_meeting_url": online_meeting_url, "available_as_saas": True}
        delta = timedelta(seconds=random.randint(1, 1000))
        live_class = {"starting_at": UTC_NOW - delta, "ending_at": UTC_NOW + delta}
        academy = {"available_as_saas": True}
        model = self.bc.database.create(
            user=1,
            group=1,
            service=service,
            live_class=live_class,
            cohort_user=1,
            cohort=cohort,
            cohort_set=1,
            cohort_set_cohort=1,
            consumable=1,
            token=1,
            academy=academy,
        )
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = (
            reverse_lazy("events:me_event_liveclass_join_hash", kwargs={"hash": model.live_class.hash})
            + f"?{querystring}"
        )

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = ""

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, online_meeting_url)

        self.assertEqual(
            self.bc.database.list_of("events.LiveClass"),
            [
                self.bc.format.to_dict(model.live_class),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            [
                self.bc.format.to_dict(model.consumable),
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("payments.ConsumptionSession"),
            [
                consumption_session(
                    model.live_class,
                    model.cohort_set,
                    model.user,
                    model.consumable,
                    data={
                        "id": 1,
                        "duration": delta,
                        "eta": UTC_NOW + delta,
                    },
                ),
            ],
        )

        self.bc.check.calls(
            tasks.end_the_consumption_session.apply_async.call_args_list,
            [
                call(args=(1, 1), eta=UTC_NOW + delta),
            ],
        )

    # Given: with Consumable, LiveClass, User have Group and Permission
    # When: Feature flag set to True and class start and end in the future
    # Then: return 200 and create a ConsumptionSession
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_with_consumable__it_try_to_consume__with_live_class__in_the_future__show_countdown(self):

        service = {"consumer": "LIVE_CLASS_JOIN"}
        online_meeting_url = self.bc.fake.url()
        cohort = {"online_meeting_url": online_meeting_url, "available_as_saas": True}
        delta = timedelta(seconds=random.randint(1, 1000))
        live_class = {"starting_at": UTC_NOW + delta, "ending_at": UTC_NOW + delta}
        academy = {"available_as_saas": True}
        model = self.bc.database.create(
            user=1,
            group=1,
            service=service,
            live_class=live_class,
            cohort_user=1,
            cohort=cohort,
            cohort_set=1,
            cohort_set_cohort=1,
            consumable=1,
            token=1,
            academy=academy,
        )
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = (
            reverse_lazy("events:me_event_liveclass_join_hash", kwargs={"hash": model.live_class.hash})
            + f"?{querystring}"
        )

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_countdown(model.live_class, model.token, academy=model.academy)

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            self.bc.database.list_of("events.LiveClass"),
            [
                self.bc.format.to_dict(model.live_class),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            [
                self.bc.format.to_dict(model.consumable),
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("payments.ConsumptionSession"),
            [
                consumption_session(
                    model.live_class,
                    model.cohort_set,
                    model.user,
                    model.consumable,
                    data={
                        "id": 1,
                        "duration": delta,
                        "eta": UTC_NOW + delta,
                    },
                ),
            ],
        )

        self.bc.check.calls(
            tasks.end_the_consumption_session.apply_async.call_args_list,
            [
                call(args=(1, 1), eta=UTC_NOW + delta),
            ],
        )

    # Given: with Consumable, LiveClass, User have Group and Permission
    # When: Feature flag set to True and class start and end in the future
    # Then: return 200 and create a ConsumptionSession
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    @patch("breathecode.events.tasks.mark_live_class_as_started.delay", MagicMock(return_value=None))
    def test_with_consumable__it_try_to_consume__with_live_class__on_starting_time(self):

        service = {"consumer": "LIVE_CLASS_JOIN"}
        online_meeting_url = self.bc.fake.url()
        cohort = {"online_meeting_url": online_meeting_url, "available_as_saas": True}
        delta = timedelta(seconds=random.randint(1, 1000))
        delta = timedelta(minutes=30)
        live_class = {"starting_at": UTC_NOW - delta, "ending_at": UTC_NOW + delta}
        academy = {"available_as_saas": True}
        model = self.bc.database.create(
            user=1,
            group=1,
            service=service,
            live_class=live_class,
            cohort_user=1,
            cohort=cohort,
            cohort_set=1,
            cohort_set_cohort=1,
            consumable=1,
            token=1,
            academy=academy,
        )
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = (
            reverse_lazy("events:me_event_liveclass_join_hash", kwargs={"hash": model.live_class.hash})
            + f"?{querystring}"
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)

        self.assertEqual(
            self.bc.database.list_of("events.LiveClass"),
            [
                self.bc.format.to_dict(model.live_class),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            [
                self.bc.format.to_dict(model.consumable),
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("payments.ConsumptionSession"),
            [
                consumption_session(
                    model.live_class,
                    model.cohort_set,
                    model.user,
                    model.consumable,
                    data={
                        "id": 1,
                        "duration": delta,
                        "eta": UTC_NOW + delta,
                    },
                ),
            ],
        )

        self.bc.check.calls(
            tasks.end_the_consumption_session.apply_async.call_args_list,
            [
                call(args=(1, 1), eta=UTC_NOW + delta),
            ],
        )
        self.bc.check.calls(tasks_events.mark_live_class_as_started.delay.call_args_list, [])

    # Given: with Consumable, LiveClass, User have Group and Permission
    # When: Feature flag set to True and class start and end in the future
    # Then: return a redirection status 302
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    @patch("breathecode.events.tasks.mark_live_class_as_started.delay", MagicMock(return_value=None))
    def test_with_consumable__it_try_to_consume__with_live_class__on_starting_time_is_teacher(self):

        service = {"consumer": "LIVE_CLASS_JOIN"}
        online_meeting_url = self.bc.fake.url()
        cohort = {"online_meeting_url": online_meeting_url, "available_as_saas": True}
        delta = timedelta(seconds=random.randint(1, 1000))
        delta = timedelta(minutes=30)
        live_class = {"starting_at": UTC_NOW - delta, "ending_at": UTC_NOW + delta}
        academy = {"available_as_saas": True}
        model = self.bc.database.create(
            user=1,
            group=1,
            service=service,
            live_class=live_class,
            cohort_user={"role": "TEACHER"},
            cohort=cohort,
            cohort_set=1,
            cohort_set_cohort=1,
            consumable=1,
            token=1,
            academy=academy,
        )
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = (
            reverse_lazy("events:me_event_liveclass_join_hash", kwargs={"hash": model.live_class.hash})
            + f"?{querystring}"
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)

        self.assertEqual(
            self.bc.database.list_of("events.LiveClass"),
            [
                self.bc.format.to_dict(model.live_class),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            [
                self.bc.format.to_dict(model.consumable),
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("payments.ConsumptionSession"),
            [
                consumption_session(
                    model.live_class,
                    model.cohort_set,
                    model.user,
                    model.consumable,
                    data={
                        "id": 1,
                        "duration": delta,
                        "eta": UTC_NOW + delta,
                    },
                ),
            ],
        )

        self.bc.check.calls(
            tasks.end_the_consumption_session.apply_async.call_args_list,
            [
                call(args=(1, 1), eta=UTC_NOW + delta),
            ],
        )
        self.bc.check.calls(
            tasks_events.mark_live_class_as_started.delay.call_args_list,
            [
                call(model.live_class.id),
            ],
        )
