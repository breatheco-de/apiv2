import os
import random
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

import capyc.pytest as capy
import pytest
from django.template import loader
from django.urls.base import reverse_lazy
from django.utils import timezone

from breathecode.events.caches import EventCache
from breathecode.payments import tasks
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

from ..mixins.new_events_tests_case import EventTestCase

UTC_NOW = timezone.now()


@pytest.fixture(autouse=True)
def setup(db):
    yield


def consumption_session(event, event_type_set, user, consumable, data={}):
    return {
        "consumable_id": consumable.id,
        "duration": timedelta(),
        "operation_code": "default",
        "eta": ...,
        "how_many": 1.0,
        "id": 0,
        "path": "payments.EventTypeSet",
        "related_id": event_type_set.id,
        "related_slug": event_type_set.slug,
        "request": {
            "args": [],
            "headers": {"academy": None},
            "kwargs": {
                "event_id": event.id,
            },
            "user": user.id,
        },
        "status": "PENDING",
        "user_id": user.id,
        "was_discounted": False,
        **data,
    }


def event_checkin_serializer(id, event, user):
    return {
        "attended_at": UTC_NOW,
        "attendee_id": user.id,
        "utm_campaign": None,
        "utm_medium": None,
        "utm_source": None,
        "utm_url": None,
        "email": user.email,
        "event_id": event.id,
        "id": id,
        "status": "DONE",
    }


# IMPORTANT: the loader.render_to_string in a function is inside of function render
def render_message(message, data={}):
    request = None
    context = {"MESSAGE": message, "BUTTON": None, "BUTTON_TARGET": "_blank", "LINK": None, **data}

    return loader.render_to_string("message.html", context, request)


def serializer(event):
    return {
        "id": event.id,
        "starting_at": event.starting_at,
        "ending_at": event.ending_at,
        "live_stream_url": event.live_stream_url,
        "title": event.title,
    }


# IMPORTANT: the loader.render_to_string in a function is inside of function render
def render_countdown(event, token, academy=None):
    request = None
    context = {
        "event": serializer(event),
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

        url = reverse_lazy("events:me_event_id_join", kwargs={"event_id": 1})

        response = self.client.get(url)

        url_hash = self.bc.format.to_base64("/v1/events/me/event/1/join")
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
        event_type_model = model = self.bc.database.create(event_type_set=1)
        model = self.bc.database.create(
            user=1,
            token=1,
            plan={"is_renewable": False, "event_type_set": event_type_model.event_type_set},
            service=1,
            subscription={"selected_event_type_set": event_type_model.event_type_set},
        )
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = reverse_lazy("events:me_event_id_join", kwargs={"event_id": 1}) + f"?{querystring}"

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

        self.assertEqual(self.bc.database.list_of("events.Event"), [])
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])
        self.assertEqual(self.bc.database.list_of("events.EventCheckin"), [])
        self.bc.check.calls(tasks.end_the_consumption_session.apply_async.call_args_list, [])

    # Given: no Consumable, Event, EventTypeSet, and IOweYou, User have Group and Permission
    # When: Feature flag set to False
    # Then: return 404
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_no_consumables__bypass_with_feature_flag__live_event_not_found(self):
        service = {"consumer": "EVENT_JOIN"}
        model = self.bc.database.create(user=1, service=service, token=1)
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = reverse_lazy("events:me_event_id_join", kwargs={"event_id": 1}) + f"?{querystring}"

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

        self.assertEqual(self.bc.database.list_of("events.Event"), [])
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])
        self.assertEqual(self.bc.database.list_of("events.EventCheckin"), [])
        self.bc.check.calls(tasks.end_the_consumption_session.apply_async.call_args_list, [])

    # Given: no Consumable, with Event, EventTypeSet, IOweYou, CohortUser, User have Group and Permission
    # When: Feature flag set to False, right hash and event.live_stream_url not set
    # Then: return 400
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_no_consumables__bypass_with_feature_flag__with_live_event__cohort_without_url(self):
        service = {"consumer": "EVENT_JOIN"}
        delta = timedelta(seconds=random.randint(1, 1000))
        event = {"starting_at": UTC_NOW - delta, "ending_at": UTC_NOW + delta}
        event_type = {"icon_url": self.bc.fake.url()}

        is_subscription = bool(random.randbytes(1))
        i_owe_you = {
            "next_payment_at": UTC_NOW + timedelta(weeks=4),
            "valid_until": UTC_NOW + timedelta(weeks=4),
        }

        if is_subscription and bool(random.randbytes(1)):
            i_owe_you["valid_until"] = None

        extra = {"subscription" if is_subscription else "plan_financing": i_owe_you}
        model = self.bc.database.create(
            user=1, service=service, event=event, event_type=event_type, event_type_set=1, token=1, **extra
        )
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = reverse_lazy("events:me_event_id_join", kwargs={"event_id": model.event.id}) + f"?{querystring}"

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_message("event-online-meeting-url-not-found")

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            self.bc.database.list_of("events.Event"),
            [
                self.bc.format.to_dict(model.event),
            ],
        )
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])
        self.assertEqual(self.bc.database.list_of("events.EventCheckin"), [])
        self.bc.check.calls(tasks.end_the_consumption_session.apply_async.call_args_list, [])

    # Given: no Consumable, with Event, EventTypeSet, IOweYou, CohortUser, User have Group and Permission
    # When: Feature flag set to False, right hash and event.live_stream_url set
    # Then: return 302 to cohort.online_meeting_url and create a EventCheckin with status DONE
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_no_consumables__bypass_with_feature_flag__with_live_event__cohort_with_url(self):
        service = {"consumer": "EVENT_JOIN"}
        online_meeting_url = self.bc.fake.url()
        delta = timedelta(seconds=random.randint(1, 1000))
        event = {
            "starting_at": UTC_NOW - delta,
            "ending_at": UTC_NOW + delta,
            "live_stream_url": online_meeting_url,
        }
        event_type = {"icon_url": self.bc.fake.url()}

        is_subscription = bool(random.randbytes(1))
        i_owe_you = {
            "next_payment_at": UTC_NOW + timedelta(weeks=4),
            "valid_until": UTC_NOW + timedelta(weeks=4),
        }

        if is_subscription and bool(random.randbytes(1)):
            i_owe_you["valid_until"] = None

        extra = {"subscription" if is_subscription else "plan_financing": i_owe_you}
        model = self.bc.database.create(
            user=1, service=service, event=event, event_type=event_type, event_type_set=1, token=1, **extra
        )
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = reverse_lazy("events:me_event_id_join", kwargs={"event_id": model.event.id}) + f"?{querystring}"

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
            self.bc.database.list_of("events.Event"),
            [
                self.bc.format.to_dict(model.event),
            ],
        )
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])
        self.assertEqual(
            self.bc.database.list_of("events.EventCheckin"),
            [
                event_checkin_serializer(1, model.event, model.user),
            ],
        )

        self.bc.check.calls(tasks.end_the_consumption_session.apply_async.call_args_list, [])

    # Given: no Consumable and Event, EventTypeSet, IOweYou, User have Group and Permission
    # When: Feature flag set to True
    # Then: return 404
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_no_consumables__it_try_to_consume__live_event_not_found(self):
        service = {"consumer": "EVENT_JOIN"}
        model = self.bc.database.create(user=1, service=service, token=1)
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = reverse_lazy("events:me_event_id_join", kwargs={"event_id": 1}) + f"?{querystring}"

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

        self.assertEqual(self.bc.database.list_of("events.Event"), [])
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])
        self.assertEqual(self.bc.database.list_of("events.EventCheckin"), [])
        self.bc.check.calls(tasks.end_the_consumption_session.apply_async.call_args_list, [])

    # Given: no Consumable with Event, EventTypeSet, IOweYou, User have Group and Permission
    # When: Feature flag set to True and event.live_stream_url not set
    # Then: return 400
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_no_consumables__it_try_to_consume__with_live_event__cohort_without_url(self):
        service = {"consumer": "EVENT_JOIN"}
        delta = timedelta(seconds=random.randint(1, 1000))
        event = {"starting_at": UTC_NOW - delta, "ending_at": UTC_NOW + delta}
        event_type = {"icon_url": self.bc.fake.url()}

        is_subscription = bool(random.randbytes(1))
        i_owe_you = {
            "next_payment_at": UTC_NOW + timedelta(weeks=4),
            "valid_until": UTC_NOW + timedelta(weeks=4),
        }

        if is_subscription and bool(random.randbytes(1)):
            i_owe_you["valid_until"] = None

        extra = {"subscription" if is_subscription else "plan_financing": i_owe_you}
        model = self.bc.database.create(
            user=1, service=service, event=event, event_type=event_type, event_type_set=1, token=1, **extra
        )
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = reverse_lazy("events:me_event_id_join", kwargs={"event_id": model.event.id}) + f"?{querystring}"

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_message("event-online-meeting-url-not-found")

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            self.bc.database.list_of("events.Event"),
            [
                self.bc.format.to_dict(model.event),
            ],
        )
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])
        self.assertEqual(self.bc.database.list_of("events.EventCheckin"), [])
        self.bc.check.calls(tasks.end_the_consumption_session.apply_async.call_args_list, [])

    # Given: no Consumable with Event, EventTypeSet, IOweYou, User have Group and Permission
    # When: Feature flag set to True and event.live_stream_url set
    # Then: return 402
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_no_consumables__it_try_to_consume__with_live_event__cohort_with_url(self):
        service = {"consumer": "EVENT_JOIN"}
        online_meeting_url = self.bc.fake.url()
        delta = timedelta(seconds=random.randint(1, 1000))
        event = {
            "host_user_id": None,
            "starting_at": UTC_NOW - delta,
            "ending_at": UTC_NOW + delta,
            "live_stream_url": online_meeting_url,
        }
        event_type = {"icon_url": self.bc.fake.url()}

        is_subscription = bool(random.randbytes(1))
        i_owe_you = {
            "next_payment_at": UTC_NOW + timedelta(weeks=4),
            "valid_until": UTC_NOW + timedelta(weeks=4),
        }

        if is_subscription and bool(random.randbytes(1)):
            i_owe_you["valid_until"] = None

        academy = {"available_as_saas": True}
        extra = {"subscription" if is_subscription else "plan_financing": i_owe_you}
        model = self.bc.database.create(
            user=1,
            academy=academy,
            service=service,
            event=event,
            event_type=event_type,
            event_type_set=1,
            plan={
                "is_renewable": False,
                "time_of_life": 1,
                "time_of_life_unit": "MONTH",
            },
            plan_offer={
                "original_plan_id": 1,
                "suggested_plan_id": 1,
                "show_modal": bool(random.getrandbits(1)),
                "expires_at": None,
            },
            token=1,
            **extra,
        )
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = reverse_lazy("events:me_event_id_join", kwargs={"event_id": model.event.id}) + f"?{querystring}"

        response = self.client.get(url)

        template_data = {}

        sugested = model.plan_offer.suggested_plan.slug
        template_data["BUTTON"] = "Get more consumables"
        template_data["LINK"] = f"https://4geeks.com/checkout?plan={sugested}&token={model.token.key}"
        template_data["GO_BACK"] = "Go back to Dashboard"
        template_data["URL_BACK"] = "https://4geeks.com/choose-program"
        content = self.bc.format.from_bytes(response.content)
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
            self.bc.database.list_of("events.Event"),
            [
                self.bc.format.to_dict(model.event),
            ],
        )
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])
        self.assertEqual(self.bc.database.list_of("events.EventCheckin"), [])
        self.bc.check.calls(tasks.end_the_consumption_session.apply_async.call_args_list, [])

    # Given: with Consumable, Event, EventTypeSet, IOweYou, User have Group and Permission
    # When: Feature flag set to True, event end in the past and event.live_stream_url set
    # Then: return 200 and create a ConsumptionSession
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_with_consumable__it_try_to_consume__with_live_event__in_the_past(self):
        service = {"consumer": "EVENT_JOIN"}
        online_meeting_url = self.bc.fake.url()
        delta = timedelta(seconds=random.randint(1, 1000))
        event = {
            "starting_at": UTC_NOW - delta,
            "ending_at": UTC_NOW - delta,
            "live_stream_url": online_meeting_url,
        }
        event_type = {"icon_url": self.bc.fake.url()}

        is_subscription = bool(random.randbytes(1))
        i_owe_you = {
            "next_payment_at": UTC_NOW + timedelta(weeks=4),
            "valid_until": UTC_NOW + timedelta(weeks=4),
        }

        if is_subscription and bool(random.randbytes(1)):
            i_owe_you["valid_until"] = None

        extra = {"subscription" if is_subscription else "plan_financing": i_owe_you}
        model = self.bc.database.create(
            user=1,
            service=service,
            event=event,
            event_type=event_type,
            event_type_set=1,
            consumable=1,
            token=1,
            **extra,
        )
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = reverse_lazy("events:me_event_id_join", kwargs={"event_id": model.event.id}) + f"?{querystring}"

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_message("event-has-ended")

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            self.bc.database.list_of("events.Event"),
            [
                self.bc.format.to_dict(model.event),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            [
                self.bc.format.to_dict(model.consumable),
            ],
        )

        self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])
        self.assertEqual(self.bc.database.list_of("events.EventCheckin"), [])
        self.bc.check.calls(tasks.end_the_consumption_session.apply_async.call_args_list, [])

    # Given: with Consumable, Event, EventTypeSet, IOweYou, User have Group and Permission
    # When: Feature flag set to True and event end in the future
    # Then: return 200 and create a ConsumptionSession and create a EventCheckin with status DONE
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_with_consumable__it_try_to_consume__with_live_event__in_the_future(self):
        service = {"consumer": "EVENT_JOIN"}
        online_meeting_url = self.bc.fake.url()
        delta = timedelta(seconds=random.randint(1, 1000))
        event = {
            "host_user_id": None,
            "starting_at": UTC_NOW - delta,
            "ending_at": UTC_NOW + delta,
            "live_stream_url": online_meeting_url,
        }
        event_type = {"icon_url": self.bc.fake.url()}

        is_subscription = bool(random.randbytes(1))
        i_owe_you = {
            "next_payment_at": UTC_NOW + timedelta(weeks=4),
            "valid_until": UTC_NOW + timedelta(weeks=4),
        }

        if is_subscription and bool(random.randbytes(1)):
            i_owe_you["valid_until"] = None

        academy = {"available_as_saas": True}
        extra = {"subscription" if is_subscription else "plan_financing": i_owe_you}
        model = self.bc.database.create(
            user=1,
            academy=academy,
            service=service,
            event=event,
            event_type=event_type,
            event_type_set=1,
            consumable=1,
            token=1,
            **extra,
        )
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = reverse_lazy("events:me_event_id_join", kwargs={"event_id": model.event.id}) + f"?{querystring}"

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
            self.bc.database.list_of("events.Event"),
            [
                self.bc.format.to_dict(model.event),
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
                    model.event,
                    model.event_type_set,
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
        self.assertEqual(
            self.bc.database.list_of("events.EventCheckin"),
            [
                event_checkin_serializer(1, model.event, model.user),
            ],
        )

        self.bc.check.calls(
            tasks.end_the_consumption_session.apply_async.call_args_list,
            [
                call(args=(1, 1), eta=UTC_NOW + delta),
            ],
        )

    # Given: with Consumable, Event, EventTypeSet, IOweYou, User have Group and Permission
    # When: Feature flag set to True and event end in the future,
    #    -> event.free_for_bootcamps = None and event_type.free_for_bootcamps = False
    #    -> academy.available_as_saas = True
    # Then: return 200 and create a ConsumptionSession and create a EventCheckin with status DONE
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_with_consumable__it_try_to_consume__with_live_event__in_the_future__academy_no_saas__non_free1(self):
        service = {"consumer": "EVENT_JOIN"}
        online_meeting_url = self.bc.fake.url()
        delta = timedelta(seconds=random.randint(1, 1000))
        event = {
            "host_user_id": None,
            "starting_at": UTC_NOW - delta,
            "ending_at": UTC_NOW + delta,
            "live_stream_url": online_meeting_url,
            "free_for_bootcamps": None,
        }
        event_type = {
            "icon_url": self.bc.fake.url(),
            "free_for_bootcamps": False,
        }

        is_subscription = bool(random.randbytes(1))
        i_owe_you = {
            "next_payment_at": UTC_NOW + timedelta(weeks=4),
            "valid_until": UTC_NOW + timedelta(weeks=4),
        }

        if is_subscription and bool(random.randbytes(1)):
            i_owe_you["valid_until"] = None

        academy = {"available_as_saas": False}
        extra = {"subscription" if is_subscription else "plan_financing": i_owe_you}
        model = self.bc.database.create(
            user=1,
            academy=academy,
            service=service,
            event=event,
            event_type=event_type,
            event_type_set=1,
            consumable=1,
            token=1,
            **extra,
        )
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = reverse_lazy("events:me_event_id_join", kwargs={"event_id": model.event.id}) + f"?{querystring}"

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
            self.bc.database.list_of("events.Event"),
            [
                self.bc.format.to_dict(model.event),
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
                    model.event,
                    model.event_type_set,
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
        self.assertEqual(
            self.bc.database.list_of("events.EventCheckin"),
            [
                event_checkin_serializer(1, model.event, model.user),
            ],
        )

        self.bc.check.calls(
            tasks.end_the_consumption_session.apply_async.call_args_list,
            [
                call(args=(1, 1), eta=UTC_NOW + delta),
            ],
        )

    # Given: with Consumable, Event, EventTypeSet, IOweYou, User have Group and Permission
    # When: Feature flag set to True and event end in the future,
    #    -> event.free_for_bootcamps = False and event_type.free_for_bootcamps is random
    #    -> academy.available_as_saas = True
    # Then: return 200 and create a ConsumptionSession and create a EventCheckin with status DONE
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_with_consumable__it_try_to_consume__with_live_event__in_the_future__academy_no_saas__non_free2(self):
        service = {"consumer": "EVENT_JOIN"}
        online_meeting_url = self.bc.fake.url()
        delta = timedelta(seconds=random.randint(1, 1000))
        event = {
            "host_user_id": None,
            "starting_at": UTC_NOW - delta,
            "ending_at": UTC_NOW + delta,
            "live_stream_url": online_meeting_url,
            "free_for_bootcamps": False,
        }
        event_type = {
            "icon_url": self.bc.fake.url(),
            "free_for_bootcamps": bool(random.randbytes(1)),
        }

        is_subscription = bool(random.randbytes(1))
        i_owe_you = {
            "next_payment_at": UTC_NOW + timedelta(weeks=4),
            "valid_until": UTC_NOW + timedelta(weeks=4),
        }

        if is_subscription and bool(random.randbytes(1)):
            i_owe_you["valid_until"] = None

        academy = {"available_as_saas": False}
        extra = {"subscription" if is_subscription else "plan_financing": i_owe_you}
        model = self.bc.database.create(
            user=1,
            academy=academy,
            service=service,
            event=event,
            event_type=event_type,
            event_type_set=1,
            consumable=1,
            token=1,
            **extra,
        )
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = reverse_lazy("events:me_event_id_join", kwargs={"event_id": model.event.id}) + f"?{querystring}"

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
            self.bc.database.list_of("events.Event"),
            [
                self.bc.format.to_dict(model.event),
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
                    model.event,
                    model.event_type_set,
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
        self.assertEqual(
            self.bc.database.list_of("events.EventCheckin"),
            [
                event_checkin_serializer(1, model.event, model.user),
            ],
        )

        self.bc.check.calls(
            tasks.end_the_consumption_session.apply_async.call_args_list,
            [
                call(args=(1, 1), eta=UTC_NOW + delta),
            ],
        )

    # Given: with Consumable, Event, EventTypeSet, IOweYou, User have Group, Permission,
    #     -> Cohort and CohortUser
    # When: Feature flag set to True and event end in the future,
    #    -> event.free_for_bootcamps = True and event_type.free_for_bootcamps = True,
    #    -> academy.available_as_saas is random,
    #    -> cohort.available_as_saas = True
    # Then: return 200 and create a ConsumptionSession and create a EventCheckin with status DONE
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_is_free_with_cohort_users_saas__cohort(self):
        service = {"consumer": "EVENT_JOIN"}

        online_meeting_url = self.bc.fake.url()
        delta = timedelta(seconds=random.randint(1, 1000))
        event = {
            "host_user_id": None,
            "starting_at": UTC_NOW - delta,
            "ending_at": UTC_NOW + delta,
            "live_stream_url": online_meeting_url,
            "free_for_bootcamps": True,
        }
        event_type = {
            "icon_url": self.bc.fake.url(),
            "free_for_bootcamps": True,
        }

        is_subscription = bool(random.randbytes(1))
        i_owe_you = {
            "next_payment_at": UTC_NOW + timedelta(weeks=4),
            "valid_until": UTC_NOW + timedelta(weeks=4),
        }

        if is_subscription and bool(random.randbytes(1)):
            i_owe_you["valid_until"] = None

        academy = {"available_as_saas": bool(random.randbytes(1))}
        cohort = {"available_as_saas": True}
        extra = {"subscription" if is_subscription else "plan_financing": i_owe_you}
        model = self.bc.database.create(
            user=1,
            academy=academy,
            service=service,
            event=event,
            event_type=event_type,
            event_type_set=1,
            cohort=cohort,
            cohort_user=1,
            consumable=1,
            token=1,
            **extra,
        )
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = reverse_lazy("events:me_event_id_join", kwargs={"event_id": model.event.id}) + f"?{querystring}"

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
            self.bc.database.list_of("events.Event"),
            [
                self.bc.format.to_dict(model.event),
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
                    model.event,
                    model.event_type_set,
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
        self.assertEqual(
            self.bc.database.list_of("events.EventCheckin"),
            [
                event_checkin_serializer(1, model.event, model.user),
            ],
        )

    # Given: with Consumable, Event, EventTypeSet, IOweYou, User have Group, Permission,
    #     -> Cohort and CohortUser
    # When: Feature flag set to True and event end in the future,
    #    -> event.free_for_bootcamps = True and event_type.free_for_bootcamps = True,
    #    -> academy.available_as_saas = True,
    #    -> cohort.available_as_saas = None
    # Then: return 200 and create a ConsumptionSession and create a EventCheckin with status DONE
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_is_free_with_cohort_users_saas__academy(self):
        service = {"consumer": "EVENT_JOIN"}
        online_meeting_url = self.bc.fake.url()
        delta = timedelta(seconds=random.randint(1, 1000))
        event = {
            "host_user_id": None,
            "starting_at": UTC_NOW - delta,
            "ending_at": UTC_NOW + delta,
            "live_stream_url": online_meeting_url,
            "free_for_bootcamps": True,
        }
        event_type = {
            "icon_url": self.bc.fake.url(),
            "free_for_bootcamps": True,
        }

        is_subscription = bool(random.randbytes(1))
        i_owe_you = {
            "next_payment_at": UTC_NOW + timedelta(weeks=4),
            "valid_until": UTC_NOW + timedelta(weeks=4),
        }

        if is_subscription and bool(random.randbytes(1)):
            i_owe_you["valid_until"] = None

        academy = {"available_as_saas": True}
        cohort = {"available_as_saas": None}
        extra = {"subscription" if is_subscription else "plan_financing": i_owe_you}
        model = self.bc.database.create(
            user=1,
            academy=academy,
            service=service,
            event=event,
            event_type=event_type,
            event_type_set=1,
            cohort=cohort,
            cohort_user=1,
            consumable=1,
            token=1,
            **extra,
        )
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = reverse_lazy("events:me_event_id_join", kwargs={"event_id": model.event.id}) + f"?{querystring}"

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
            self.bc.database.list_of("events.Event"),
            [
                self.bc.format.to_dict(model.event),
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
                    model.event,
                    model.event_type_set,
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
        self.assertEqual(
            self.bc.database.list_of("events.EventCheckin"),
            [
                event_checkin_serializer(1, model.event, model.user),
            ],
        )

    # Given: with Consumable, Event, EventTypeSet, IOweYou, User have Group, Permission,
    #     -> Cohort and CohortUser
    # When: Feature flag set to True and event end in the future,
    #    -> event.free_for_bootcamps = True and event_type.free_for_bootcamps = True,
    #    -> academy.available_as_saas is random,
    #    -> cohort.available_as_saas = False
    # Then: return 200 and create a ConsumptionSession and create a EventCheckin with status DONE
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_is_free_with_cohort_users_no_saas__cohort(self):
        service = {"consumer": "EVENT_JOIN"}
        online_meeting_url = self.bc.fake.url()
        delta = timedelta(seconds=random.randint(1, 1000))
        event = {
            "host_user_id": None,
            "starting_at": UTC_NOW - delta,
            "ending_at": UTC_NOW + delta,
            "live_stream_url": online_meeting_url,
            "free_for_bootcamps": True,
        }
        event_type = {
            "icon_url": self.bc.fake.url(),
            "free_for_bootcamps": True,
        }

        is_subscription = bool(random.randbytes(1))
        i_owe_you = {
            "next_payment_at": UTC_NOW + timedelta(weeks=4),
            "valid_until": UTC_NOW + timedelta(weeks=4),
        }

        if is_subscription and bool(random.randbytes(1)):
            i_owe_you["valid_until"] = None

        academy = {"available_as_saas": bool(random.randbytes(1))}
        cohort = {"available_as_saas": False}
        extra = {"subscription" if is_subscription else "plan_financing": i_owe_you}
        model = self.bc.database.create(
            user=1,
            academy=academy,
            service=service,
            event=event,
            event_type=event_type,
            event_type_set=1,
            cohort=cohort,
            cohort_user=1,
            consumable=1,
            token=1,
            **extra,
        )
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = reverse_lazy("events:me_event_id_join", kwargs={"event_id": model.event.id}) + f"?{querystring}"

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
            self.bc.database.list_of("events.Event"),
            [
                self.bc.format.to_dict(model.event),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            [
                self.bc.format.to_dict(model.consumable),
            ],
        )

        self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])
        self.assertEqual(
            self.bc.database.list_of("events.EventCheckin"),
            [
                event_checkin_serializer(1, model.event, model.user),
            ],
        )

    # Given: with Consumable, Event, EventTypeSet, IOweYou, User have Group, Permission,
    #     -> Cohort and CohortUser
    # When: Feature flag set to True and event end in the future,
    #    -> event.free_for_bootcamps = True and event_type.free_for_bootcamps = True,
    #    -> academy.available_as_saas = False,
    #    -> cohort.available_as_saas = None
    # Then: return 200 and create a ConsumptionSession and create a EventCheckin with status DONE
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_is_free_with_cohort_users_no_saas__academy(self):
        service = {"consumer": "EVENT_JOIN"}
        online_meeting_url = self.bc.fake.url()
        delta = timedelta(seconds=random.randint(1, 1000))
        event = {
            "host_user_id": None,
            "starting_at": UTC_NOW - delta,
            "ending_at": UTC_NOW + delta,
            "live_stream_url": online_meeting_url,
            "free_for_bootcamps": True,
        }
        event_type = {
            "icon_url": self.bc.fake.url(),
            "free_for_bootcamps": True,
        }

        is_subscription = bool(random.randbytes(1))
        i_owe_you = {
            "next_payment_at": UTC_NOW + timedelta(weeks=4),
            "valid_until": UTC_NOW + timedelta(weeks=4),
        }

        if is_subscription and bool(random.randbytes(1)):
            i_owe_you["valid_until"] = None

        academy = {"available_as_saas": False}
        cohort = {"available_as_saas": None}
        extra = {"subscription" if is_subscription else "plan_financing": i_owe_you}
        model = self.bc.database.create(
            user=1,
            academy=academy,
            service=service,
            event=event,
            event_type=event_type,
            event_type_set=1,
            cohort=cohort,
            cohort_user=1,
            consumable=1,
            token=1,
            **extra,
        )
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = reverse_lazy("events:me_event_id_join", kwargs={"event_id": model.event.id}) + f"?{querystring}"

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
            self.bc.database.list_of("events.Event"),
            [
                self.bc.format.to_dict(model.event),
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            [
                self.bc.format.to_dict(model.consumable),
            ],
        )

        self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])
        self.assertEqual(
            self.bc.database.list_of("events.EventCheckin"),
            [
                event_checkin_serializer(1, model.event, model.user),
            ],
        )

    # Given: with Consumable, Event, EventTypeSet, IOweYou, User have Group and Permission
    # When: Feature flag set to True and event start and end in the future
    # Then: return 200 and create a ConsumptionSession
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_with_consumable__it_try_to_consume__with_live_event__in_the_future__show_countdown(self):
        service = {"consumer": "EVENT_JOIN"}
        online_meeting_url = self.bc.fake.url()
        delta = timedelta(seconds=random.randint(1, 1000))
        event = {
            "host_user_id": None,
            "starting_at": UTC_NOW + delta,
            "ending_at": UTC_NOW + delta,
            "live_stream_url": online_meeting_url,
        }
        event_type = {"icon_url": self.bc.fake.url()}

        is_subscription = bool(random.randbytes(1))
        i_owe_you = {
            "next_payment_at": UTC_NOW + timedelta(weeks=4),
            "valid_until": UTC_NOW + timedelta(weeks=4),
        }

        if is_subscription and bool(random.randbytes(1)):
            i_owe_you["valid_until"] = None

        academy = {"available_as_saas": True}
        extra = {"subscription" if is_subscription else "plan_financing": i_owe_you}
        model = self.bc.database.create(
            user=1,
            academy=academy,
            service=service,
            event=event,
            event_type=event_type,
            event_type_set=1,
            consumable=1,
            token=1,
            **extra,
        )
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = reverse_lazy("events:me_event_id_join", kwargs={"event_id": model.event.id}) + f"?{querystring}"

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_countdown(model.event, model.token, academy=model.academy)

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            self.bc.database.list_of("events.Event"),
            [
                self.bc.format.to_dict(model.event),
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
                    model.event,
                    model.event_type_set,
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
        self.assertEqual(self.bc.database.list_of("events.EventCheckin"), [])

        self.bc.check.calls(
            tasks.end_the_consumption_session.apply_async.call_args_list,
            [
                call(args=(1, 1), eta=UTC_NOW + delta),
            ],
        )

    # Given: with Consumable, Event, EventTypeSet, IOweYou, User have Group and Permission
    # When: Feature flag set to True and event start and end in the future,
    #    -> authenticate user is event host
    # Then: return 200 and avoid to create a ConsumptionSession
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_with_consumable__it_try_to_consume__with_live_event__in_the_future__show_countdown(self):
        service = {"consumer": "EVENT_JOIN"}
        online_meeting_url = self.bc.fake.url()
        delta = timedelta(seconds=random.randint(1, 1000))
        event = {
            "host_user_id": 1,
            "starting_at": UTC_NOW + delta,
            "ending_at": UTC_NOW + delta,
            "live_stream_url": online_meeting_url,
        }
        event_type = {"icon_url": self.bc.fake.url()}

        is_subscription = bool(random.randbytes(1))
        i_owe_you = {
            "next_payment_at": UTC_NOW + timedelta(weeks=4),
            "valid_until": UTC_NOW + timedelta(weeks=4),
        }

        if is_subscription and bool(random.randbytes(1)):
            i_owe_you["valid_until"] = None

        academy = {"available_as_saas": True}
        extra = {"subscription" if is_subscription else "plan_financing": i_owe_you}
        model = self.bc.database.create(
            user=1,
            academy=academy,
            service=service,
            event=event,
            event_type=event_type,
            # event_type_set=1,
            # consumable=1,
            token=1,
            **extra,
        )
        querystring = self.bc.format.to_querystring({"token": model.token.key})

        url = reverse_lazy("events:me_event_id_join", kwargs={"event_id": model.event.id}) + f"?{querystring}"

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_countdown(model.event, model.token, academy=model.academy)

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            self.bc.database.list_of("events.Event"),
            [
                self.bc.format.to_dict(model.event),
            ],
        )
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])

        self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])
        self.assertEqual(self.bc.database.list_of("events.EventCheckin"), [])

        self.bc.check.calls(tasks.end_the_consumption_session.apply_async.call_args_list, [])


# Given: A no SAAS student who has paid
# When: auth
# Then: response 200
@pytest.mark.parametrize(
    "cohort_user",
    [
        {
            "finantial_status": "FULLY_PAID",
            "educational_status": "ACTIVE",
        },
        {
            "finantial_status": "UP_TO_DATE",
            "educational_status": "ACTIVE",
        },
        {
            "finantial_status": "FULLY_PAID",
            "educational_status": "GRADUATED",
        },
        {
            "finantial_status": "UP_TO_DATE",
            "educational_status": "GRADUATED",
        },
    ],
)
@pytest.mark.parametrize(
    "academy, cohort",
    [
        (
            {"available_as_saas": True},
            {"available_as_saas": False},
        ),
        (
            {"available_as_saas": False},
            {"available_as_saas": None},
        ),
    ],
)
@patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
@patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
@patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
@patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
def test__post__auth__no_saas__finantial_status_no_late(
    bc: Breathecode, client: capy.Client, academy, cohort, cohort_user
):
    service = {"consumer": "EVENT_JOIN"}
    online_meeting_url = bc.fake.url()
    delta = timedelta(seconds=random.randint(1, 1000))
    event = {
        "host_user_id": 1,
        "starting_at": UTC_NOW + delta,
        "ending_at": UTC_NOW + delta,
        "live_stream_url": online_meeting_url,
    }
    event_type = {"icon_url": bc.fake.url()}

    is_subscription = bool(random.randbytes(1))
    i_owe_you = {
        "next_payment_at": UTC_NOW + timedelta(weeks=4),
        "valid_until": UTC_NOW + timedelta(weeks=4),
    }

    if is_subscription and bool(random.randbytes(1)):
        i_owe_you["valid_until"] = None

    extra = {"subscription" if is_subscription else "plan_financing": i_owe_you}
    model = bc.database.create(
        user=1,
        academy=academy,
        cohort=cohort,
        cohort_user=cohort_user,
        service=service,
        event=event,
        event_type=event_type,
        token=1,
        **extra,
    )
    querystring = bc.format.to_querystring({"token": model.token.key})

    url = reverse_lazy("events:me_event_id_join", kwargs={"event_id": model.event.id}) + f"?{querystring}"

    response = client.get(url)

    content = bc.format.from_bytes(response.content)
    expected = render_countdown(model.event, model.token, academy=model.academy)

    # dump error in external files
    if content != expected:
        with open("content.html", "w") as f:
            f.write(content)

        with open("expected.html", "w") as f:
            f.write(expected)

    assert content, expected
    assert response.status_code == 200

    assert bc.database.list_of("events.Event") == [
        bc.format.to_dict(model.event),
    ]
    assert bc.database.list_of("payments.Consumable") == []

    assert bc.database.list_of("payments.ConsumptionSession") == []
    assert bc.database.list_of("events.EventCheckin") == []

    bc.check.calls(tasks.end_the_consumption_session.apply_async.call_args_list, [])


# Given: A no SAAS student who hasn't paid
# When: auth
# Then: response 402
@pytest.mark.parametrize(
    "academy, cohort",
    [
        (
            {"available_as_saas": True},
            {"available_as_saas": False},
        ),
        (
            {"available_as_saas": False},
            {"available_as_saas": None},
        ),
    ],
)
@patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
@patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
@patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
@patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
def test__post__auth__no_saas__finantial_status_late(bc: Breathecode, client: capy.Client, academy, cohort):
    service = {"consumer": "EVENT_JOIN"}
    online_meeting_url = bc.fake.url()
    delta = timedelta(seconds=random.randint(1, 1000))
    event = {
        "host_user_id": 1,
        "starting_at": UTC_NOW + delta,
        "ending_at": UTC_NOW + delta,
        "live_stream_url": online_meeting_url,
    }
    event_type = {"icon_url": bc.fake.url()}

    is_subscription = bool(random.randbytes(1))
    i_owe_you = {
        "next_payment_at": UTC_NOW + timedelta(weeks=4),
        "valid_until": UTC_NOW + timedelta(weeks=4),
    }

    if is_subscription and bool(random.randbytes(1)):
        i_owe_you["valid_until"] = None

    extra = {"subscription" if is_subscription else "plan_financing": i_owe_you}
    cohort_user = {"finantial_status": "LATE", "educational_status": "ACTIVE"}
    model = bc.database.create(
        user=1,
        academy=academy,
        cohort=cohort,
        cohort_user=cohort_user,
        service=service,
        event=event,
        event_type=event_type,
        token=1,
        **extra,
    )
    querystring = bc.format.to_querystring({"token": model.token.key})

    url = reverse_lazy("events:me_event_id_join", kwargs={"event_id": model.event.id}) + f"?{querystring}"

    response = client.get(url)

    content = bc.format.from_bytes(response.content)
    expected = render_message(
        "You must get a plan in order to access this service",
        data={
            "GO_BACK": "Go back to Dashboard",
            "URL_BACK": "https://4geeks.com/choose-program",
            "BUTTON": "Get a plan",
            "LINK": f"https://4geeks.com/checkout?plan=basic&token={model.token.key}",
        },
    )

    # dump error in external files
    if content != expected:
        with open("content.html", "w") as f:
            f.write(content)

        with open("expected.html", "w") as f:
            f.write(expected)

    assert content == expected
    assert response.status_code == 402

    assert bc.database.list_of("events.Event") == [
        bc.format.to_dict(model.event),
    ]
    assert bc.database.list_of("payments.Consumable") == []

    assert bc.database.list_of("payments.ConsumptionSession") == []
    assert bc.database.list_of("events.EventCheckin") == []

    bc.check.calls(tasks.end_the_consumption_session.apply_async.call_args_list, [])
