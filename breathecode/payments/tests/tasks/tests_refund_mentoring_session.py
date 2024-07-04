"""
Test /answer
"""

import logging
import random
from unittest.mock import MagicMock, call

import pytest
from django.utils import timezone

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
from capyc.django.pytest.fixtures import QuerySet

from ...tasks import refund_mentoring_session

UTC_NOW = timezone.now()


@pytest.fixture
def get_queryset_pks(queryset: QuerySet):
    yield queryset.get_pks


@pytest.fixture(autouse=True)
def setup_db(db, monkeypatch, enable_signals):
    enable_signals(
        "breathecode.payments.signals.consume_service",
        "breathecode.payments.signals.grant_service_permissions",
        "breathecode.payments.signals.lose_service_permissions",
        "breathecode.payments.signals.reimburse_service_units",  #
    )
    monkeypatch.setattr("logging.Logger.info", MagicMock())
    monkeypatch.setattr("logging.Logger.error", MagicMock())
    monkeypatch.setattr("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    yield


# When: no mentoring session
# Then: do nothing
def test_0_items(bc: Breathecode):
    refund_mentoring_session.delay(1)

    bc.check.calls(
        logging.Logger.info.call_args_list,
        [
            call("Starting refund_mentoring_session for mentoring session 1"),
        ],
    )
    bc.check.calls(
        logging.Logger.error.call_args_list,
        [
            call("MentoringSession with id 1 not found or is invalid", exc_info=True),
        ],
    )

    assert bc.database.list_of("mentorship.MentorshipSession") == []
    assert bc.database.list_of("payments.ConsumptionSession") == []
    assert bc.database.list_of("payments.Consumable") == []


# Given: 1 MentoringSession
# When: not have mentee, service and have a bad status
# Then: not found mentorship session
def test_1_mentoring_session__nothing_provide(bc: Breathecode):
    model = bc.database.create(mentorship_session=1)

    # remove prints from mixer
    logging.Logger.info.call_args_list = []
    logging.Logger.error.call_args_list = []

    refund_mentoring_session.delay(1)

    bc.check.calls(
        logging.Logger.info.call_args_list,
        [
            call("Starting refund_mentoring_session for mentoring session 1"),
        ],
    )
    bc.check.calls(
        logging.Logger.error.call_args_list,
        [
            call("MentoringSession with id 1 not found or is invalid", exc_info=True),
        ],
    )

    assert bc.database.list_of("mentorship.MentorshipSession") == [
        bc.format.to_dict(model.mentorship_session),
    ]
    assert bc.database.list_of("payments.ConsumptionSession") == []
    assert bc.database.list_of("payments.Consumable") == []


# Given: 1 MentoringSession and 1 User
# When: have mentee and not have service and have a bad status
# Then: not found mentorship session
def test_1_mentoring_session__just_with_mentee(bc: Breathecode, get_queryset_pks):
    user = {"groups": []}
    model = bc.database.create(mentorship_session=1, user=user, group=1, permission=1)

    # remove prints from mixer
    logging.Logger.info.call_args_list = []
    logging.Logger.error.call_args_list = []

    refund_mentoring_session.delay(1)

    bc.check.calls(
        logging.Logger.info.call_args_list,
        [
            call("Starting refund_mentoring_session for mentoring session 1"),
        ],
    )
    bc.check.calls(
        logging.Logger.error.call_args_list,
        [
            call("MentoringSession with id 1 not found or is invalid", exc_info=True),
        ],
    )

    assert bc.database.list_of("mentorship.MentorshipSession") == [
        bc.format.to_dict(model.mentorship_session),
    ]
    assert bc.database.list_of("payments.ConsumptionSession") == []
    assert bc.database.list_of("payments.Consumable") == []

    get_queryset_pks(model.user.groups.all()) == []


# Given: 1 MentoringSession and 1 MentorshipService
# When: have service and not have mentee and have a bad status
# Then: not found mentorship session
def test_1_mentoring_session__just_with_service(bc: Breathecode):
    model = bc.database.create(mentorship_session=1, mentorship_service=1)

    # remove prints from mixer
    logging.Logger.info.call_args_list = []
    logging.Logger.error.call_args_list = []

    refund_mentoring_session.delay(1)

    bc.check.calls(
        logging.Logger.info.call_args_list,
        [
            call("Starting refund_mentoring_session for mentoring session 1"),
        ],
    )
    bc.check.calls(
        logging.Logger.error.call_args_list,
        [
            call("MentoringSession with id 1 not found or is invalid", exc_info=True),
        ],
    )

    assert bc.database.list_of("mentorship.MentorshipSession") == [
        bc.format.to_dict(model.mentorship_session),
    ]
    assert bc.database.list_of("payments.ConsumptionSession") == []
    assert bc.database.list_of("payments.Consumable") == []


# Given: 1 MentoringSession
# When: not have service, mentee and have a right status
# Then: not found mentorship session
def test_1_mentoring_session__just_with_right_status(bc: Breathecode):
    mentorship_session = {"status": random.choice(["PENDING", "STARTED", "COMPLETED"])}
    model = bc.database.create(mentorship_session=mentorship_session)

    # remove prints from mixer
    logging.Logger.info.call_args_list = []
    logging.Logger.error.call_args_list = []

    refund_mentoring_session.delay(1)

    bc.check.calls(
        logging.Logger.info.call_args_list,
        [
            call("Starting refund_mentoring_session for mentoring session 1"),
        ],
    )
    bc.check.calls(
        logging.Logger.error.call_args_list,
        [
            call("MentoringSession with id 1 not found or is invalid", exc_info=True),
        ],
    )

    assert bc.database.list_of("mentorship.MentorshipSession") == [
        bc.format.to_dict(model.mentorship_session),
    ]
    assert bc.database.list_of("payments.ConsumptionSession") == []
    assert bc.database.list_of("payments.Consumable") == []


# Given: 1 MentoringSession, 1 User and 1 MentorshipService
# When: have service, mentee and have a right status
# Then: not found mentorship session
def test_1_mentoring_session__all_elements_given(bc: Breathecode, get_queryset_pks):
    mentorship_session = {"status": random.choice(["FAILED", "IGNORED"])}

    user = {"groups": []}
    model = bc.database.create(
        mentorship_session=mentorship_session, user=user, mentorship_service=1, group=1, permission=1
    )

    # remove prints from mixer
    logging.Logger.info.call_args_list = []
    logging.Logger.error.call_args_list = []

    refund_mentoring_session.delay(1)

    bc.check.calls(
        logging.Logger.info.call_args_list,
        [
            call("Starting refund_mentoring_session for mentoring session 1"),
        ],
    )
    bc.check.calls(
        logging.Logger.error.call_args_list,
        [
            call("ConsumptionSession not found for mentorship session 1", exc_info=True),
        ],
    )

    assert bc.database.list_of("mentorship.MentorshipSession") == [
        bc.format.to_dict(model.mentorship_session),
    ]
    assert bc.database.list_of("payments.ConsumptionSession") == []
    assert bc.database.list_of("payments.Consumable") == []

    get_queryset_pks(model.user.groups.all()) == []


# Given: 1 MentoringSession, 1 User, 1 ConsumptionSession, 1 Consumable and 1 MentorshipServiceSet
# When: consumption session is pending
# Then: not refund consumable
def test_consumption_session_is_pending(bc: Breathecode, get_queryset_pks):
    mentorship_session = {"status": random.choice(["FAILED", "IGNORED"])}
    how_many_consumables = random.randint(1, 10)
    how_mawy_will_consume = random.randint(1, how_many_consumables)
    consumable = {"how_many": how_many_consumables}
    consumption_session = {"how_many": how_mawy_will_consume, "status": "PENDING"}

    user = {"groups": []}
    model = bc.database.create(
        mentorship_session=mentorship_session,
        user=user,
        mentorship_service=1,
        consumption_session=consumption_session,
        consumable=consumable,
        mentorship_service_set=1,
        group=1,
        permission=1,
    )

    # remove prints from mixer
    logging.Logger.info.call_args_list = []
    logging.Logger.error.call_args_list = []

    refund_mentoring_session.delay(1)

    bc.check.calls(
        logging.Logger.info.call_args_list,
        [
            call("Starting refund_mentoring_session for mentoring session 1"),
        ],
    )
    bc.check.calls(logging.Logger.error.call_args_list, [])

    assert bc.database.list_of("mentorship.MentorshipSession") == [
        bc.format.to_dict(model.mentorship_session),
    ]

    assert bc.database.list_of("payments.ConsumptionSession") == [
        {
            **bc.format.to_dict(model.consumption_session),
            "status": "CANCELLED",
        },
    ]

    assert bc.database.list_of("payments.Consumable") == [
        bc.format.to_dict(model.consumable),
    ]

    get_queryset_pks(model.user.groups.all()) == []


# Given: 1 MentoringSession, 1 User, 1 ConsumptionSession, 1 Consumable and 1 MentorshipServiceSet
# When: consumption session is done
# Then: not refund consumable
def test_consumption_session_is_done(bc: Breathecode, get_queryset_pks):
    mentorship_session = {"status": random.choice(["FAILED", "IGNORED"])}
    how_many_consumables = random.randint(1, 10)
    how_mawy_will_consume = random.randint(1, 10)
    consumable = {"how_many": how_many_consumables}
    consumption_session = {"how_many": how_mawy_will_consume, "status": "DONE"}

    user = {"groups": []}
    model = bc.database.create(
        mentorship_session=mentorship_session,
        user=user,
        mentorship_service=1,
        consumption_session=consumption_session,
        consumable=consumable,
        mentorship_service_set=1,
        group=1,
        permission=1,
    )

    # remove prints from mixer
    logging.Logger.info.call_args_list = []
    logging.Logger.error.call_args_list = []

    refund_mentoring_session.delay(1)

    bc.check.calls(
        logging.Logger.info.call_args_list,
        [
            call("Starting refund_mentoring_session for mentoring session 1"),
            call("Refunding consumption session because it was discounted"),
        ],
    )
    bc.check.calls(logging.Logger.error.call_args_list, [])

    assert bc.database.list_of("mentorship.MentorshipSession") == [
        bc.format.to_dict(model.mentorship_session),
    ]

    assert bc.database.list_of("payments.ConsumptionSession") == [
        {
            **bc.format.to_dict(model.consumption_session),
            "status": "CANCELLED",
        },
    ]

    assert bc.database.list_of("payments.Consumable") == [
        {
            **bc.format.to_dict(model.consumable),
            "how_many": how_many_consumables + how_mawy_will_consume,
        }
    ]

    get_queryset_pks(model.user.groups.all()) == []


# Given: 1 MentoringSession, 1 User, 1 ConsumptionSession, 1 Consumable and 1 MentorshipServiceSet
# When: consumption session is done
# Then: not refund consumable
def test_consumption_session_is_cancelled(bc: Breathecode, get_queryset_pks):
    mentorship_session = {"status": random.choice(["FAILED", "IGNORED"])}
    how_many_consumables = random.randint(1, 10)
    how_mawy_will_consume = random.randint(1, 10)
    consumable = {"how_many": how_many_consumables}
    consumption_session = {"how_many": how_mawy_will_consume, "status": "CANCELLED"}

    user = {"groups": []}
    model = bc.database.create(
        mentorship_session=mentorship_session,
        user=user,
        mentorship_service=1,
        consumption_session=consumption_session,
        consumable=consumable,
        mentorship_service_set=1,
        group=1,
        permission=1,
    )

    # remove prints from mixer
    logging.Logger.info.call_args_list = []
    logging.Logger.error.call_args_list = []

    refund_mentoring_session.delay(1)

    bc.check.calls(
        logging.Logger.info.call_args_list,
        [
            call("Starting refund_mentoring_session for mentoring session 1"),
        ],
    )
    bc.check.calls(
        logging.Logger.error.call_args_list,
        [
            call("ConsumptionSession not found for mentorship session 1", exc_info=True),
        ],
    )

    assert bc.database.list_of("mentorship.MentorshipSession") == [
        bc.format.to_dict(model.mentorship_session),
    ]

    assert bc.database.list_of("payments.ConsumptionSession") == [
        bc.format.to_dict(model.consumption_session),
    ]

    assert bc.database.list_of("payments.Consumable") == [
        bc.format.to_dict(model.consumable),
    ]

    get_queryset_pks(model.user.groups.all()) == []


# Given: 1 MentoringSession, 1 User, 1 ConsumptionSession, 1 Consumable and 1 MentorshipServiceSet
# When: consumption session is done and consumable how many is 0
# Then: not refund consumable
def test_consumable_wasted(bc: Breathecode, get_queryset_pks):
    mentorship_session = {"status": random.choice(["FAILED", "IGNORED"])}
    how_many_consumables = 0
    how_mawy_will_consume = random.randint(1, 10)
    consumable = {"how_many": how_many_consumables}
    consumption_session = {"how_many": how_mawy_will_consume, "status": "DONE"}

    user = {"groups": []}
    groups = [{"permissions": n} for n in range(1, 4)]
    model = bc.database.create(
        mentorship_session=mentorship_session,
        user=user,
        mentorship_service=1,
        consumption_session=consumption_session,
        consumable=consumable,
        mentorship_service_set=1,
        group=groups,
        permission=2,
    )

    # remove prints from mixer
    logging.Logger.info.call_args_list = []
    logging.Logger.error.call_args_list = []

    refund_mentoring_session.delay(1)

    bc.check.calls(
        logging.Logger.info.call_args_list,
        [
            call("Starting refund_mentoring_session for mentoring session 1"),
            call("Refunding consumption session because it was discounted"),
        ],
    )
    bc.check.calls(logging.Logger.error.call_args_list, [])

    assert bc.database.list_of("mentorship.MentorshipSession") == [
        bc.format.to_dict(model.mentorship_session),
    ]

    assert bc.database.list_of("payments.ConsumptionSession") == [
        {
            **bc.format.to_dict(model.consumption_session),
            "status": "CANCELLED",
        },
    ]

    assert bc.database.list_of("payments.Consumable") == [
        {
            **bc.format.to_dict(model.consumable),
            "how_many": how_many_consumables + how_mawy_will_consume,
        }
    ]

    assert get_queryset_pks(model.user.groups.all()) == [1, 2, 3]
