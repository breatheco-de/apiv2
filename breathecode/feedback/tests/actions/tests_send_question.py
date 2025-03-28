"""
Test /answer
"""

import random
from copy import copy
from unittest.mock import MagicMock, call

import pytest
from capyc import pytest as capy

import breathecode.notify.actions as notify_actions
from breathecode.authenticate.models import Token
from breathecode.feedback.models import Answer

from ...actions import send_question, strings


def get_translations(lang, template):
    return {
        "title": strings[lang][template]["title"],
        "highest": strings[lang][template]["highest"],
        "lowest": strings[lang][template]["lowest"],
        "survey_subject": strings[lang][template]["survey_subject"],
    }


@pytest.fixture(autouse=True)
def setup(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    monkeypatch.setattr(
        "breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None)
    )
    monkeypatch.setattr("breathecode.notify.actions.send_email_message", MagicMock(return_value=None))
    monkeypatch.setattr("breathecode.notify.actions.send_slack", MagicMock(return_value=None))


def get_token_key(id=None):
    kwargs = {}
    if id:
        kwargs["id"] = id
    return Token.objects.filter(**kwargs).values_list("key", flat=True).first()


def get_serializer(data={}):
    return {
        "id": 0,
        "title": "",
        "lowest": None,
        "highest": None,
        "lang": "en",
        "event_id": None,
        "mentor_id": None,
        "cohort_id": 0,
        "academy_id": None,
        "token_id": None,
        "score": None,
        "comment": None,
        "mentorship_session_id": None,
        "sent_at": None,
        "survey_id": None,
        "status": "PENDING",
        "user_id": 0,
        "opened_at": None,
        "question_by_slug": None,
        "asset_id": None,
        "live_class_id": None,
        **data,
    }


def get_email_call(lang, template, params, user, academy, token):
    t = get_translations(lang, template)
    params = copy(params)
    while True:
        if len(params) == 0:
            break

        value = params.pop(0)

        if "{}" not in t["title"]:
            break

        t["title"] = t["title"].replace("{}", value, 1)

    button = "Answer" if lang == "en" else "Responder"

    return call(
        "nps",
        user.email,
        {
            "QUESTION": t["title"],
            "HIGHEST": t["highest"],
            "LOWEST": t["lowest"],
            "SUBJECT": t["title"],
            "ANSWER_ID": 1,
            "BUTTON": button,
            "LINK": f"https://nps.4geeks.com/1?token={token.key}",
        },
        academy=academy,
    )


def get_slack_call(lang, template, params, slack_user, slack_team, academy, token):
    t = get_translations(lang, template)
    params = copy(params)
    while True:
        if len(params) == 0:
            break

        value = params.pop(0)

        if "{}" not in t["title"]:
            break

        t["title"] = t["title"].replace("{}", value, 1)

    button = "Answer" if lang == "en" else "Responder"

    return call(
        "nps",
        slack_user,
        slack_team,
        data={
            "QUESTION": t["title"],
            "HIGHEST": t["highest"],
            "LOWEST": t["lowest"],
            "SUBJECT": t["title"],
            "ANSWER_ID": 1,
            "BUTTON": button,
            "LINK": f"https://nps.4geeks.com/1?token={token.key}",
        },
        academy=academy,
    )


def test_send_question__without_cohort(database: capy.Database):
    model = database.create(user=True)

    try:
        send_question(model["user"])
    except Exception as e:
        assert str(e) == "without-cohort-or-cannot-determine-cohort"

    assert database.list_of("feedback.Answer") == []
    assert notify_actions.send_email_message.call_args_list == []
    assert notify_actions.send_slack.call_args_list == []


# """
# 🔽🔽🔽 Can't determine the Cohort
# """


def test_send_question__with_same_user_in_two_cohort(database: capy.Database):
    cohort_user = {"educational_status": random.choice(["POSTPONED", "SUSPENDED", "DROPPED"])}

    model1 = database.create(
        city=1,
        country=1,
        cohort_user=(2, cohort_user),
        survey_template=[
            {"lang": "en", "is_shared": True, "when_asking_cohort": get_translations("en", "cohort")},
            {"lang": "es", "is_shared": True, "when_asking_cohort": get_translations("es", "cohort"), "original_id": 1},
        ],
    )

    try:
        send_question(model1["user"])
    except Exception as e:
        assert str(e) == "without-cohort-or-cannot-determine-cohort"

    assert database.list_of("feedback.Answer") == []
    assert notify_actions.send_email_message.call_args_list == []
    assert notify_actions.send_slack.call_args_list == []


# """
# 🔽🔽🔽 Cohort without SyllabusVersion
# """


@pytest.mark.parametrize(
    "survey_template",
    [
        [
            {"lang": "en", "is_shared": True, "when_asking_cohort": get_translations("en", "cohort")},
            {"lang": "es", "is_shared": True, "when_asking_cohort": get_translations("es", "cohort"), "original_id": 1},
        ],
    ],
)
@pytest.mark.parametrize("status", ["ACTIVE", "GRADUATED"])
def test_send_question__cohort_without_syllabus_version(
    database: capy.Database, status: str, survey_template: list[dict]
):
    cohort_user = {"educational_status": status}

    model = database.create(
        city=1,
        country=1,
        user=True,
        cohort_user=cohort_user,
        survey_template=survey_template,
    )

    try:
        send_question(model["user"])
    except Exception as e:
        message = str(e)
        assert message == "cohort-without-syllabus-version"

    translations = strings[model["cohort"].language]
    expected = [
        get_serializer(
            {
                "id": 1,
                "title": "",
                "lowest": translations["event"]["lowest"],
                "highest": translations["event"]["highest"],
                "lang": "en",
                "cohort_id": 1,
                "status": "PENDING",
                "user_id": 1,
            }
        ),
    ]

    assert database.list_of("feedback.Answer") == expected
    assert notify_actions.send_email_message.call_args_list == []
    assert notify_actions.send_slack.call_args_list == []


# """
# 🔽🔽🔽 Cohort without SyllabusSchedule
# """


@pytest.mark.parametrize(
    "survey_template",
    [
        [
            {"lang": "en", "is_shared": True, "when_asking_cohort": get_translations("en", "cohort")},
            {"lang": "es", "is_shared": True, "when_asking_cohort": get_translations("es", "cohort"), "original_id": 1},
        ],
    ],
)
@pytest.mark.parametrize("status", ["ACTIVE", "GRADUATED"])
def test_send_question__cohort_without_syllabus_schedule(
    database: capy.Database, status: str, survey_template: list[dict]
):
    cohort_user = {"educational_status": status}

    model = database.create(
        city=1,
        country=1,
        user=True,
        cohort_user=cohort_user,
        syllabus_version=True,
        survey_template=survey_template,
    )

    try:
        send_question(model["user"])
    except Exception as e:
        message = str(e)
        assert message == "cohort-without-specialty-mode"

    translations = strings[model["cohort"].language]
    expected = [
        get_serializer(
            {
                "id": 1,
                "title": "",
                "lowest": translations["event"]["lowest"],
                "highest": translations["event"]["highest"],
                "lang": "en",
                "cohort_id": 1,
                "token_id": None,
                "status": "PENDING",
                "user_id": 1,
            }
        ),
    ]

    assert database.list_of("feedback.Answer") == expected
    assert notify_actions.send_email_message.call_args_list == []
    assert notify_actions.send_slack.call_args_list == []


# """
# 🔽🔽🔽 Answer are generate and send in a email
# """


@pytest.mark.parametrize(
    "survey_template",
    [
        [
            {"lang": "en", "is_shared": True, "when_asking_cohort": get_translations("en", "cohort")},
            {"lang": "es", "is_shared": True, "when_asking_cohort": get_translations("es", "cohort"), "original_id": 1},
        ],
    ],
)
@pytest.mark.parametrize("status", ["ACTIVE", "GRADUATED"])
def test_send_question__just_send_by_email(
    database: capy.Database, fake: capy.Fake, status: str, survey_template: list[dict]
):
    cohort_user = {"educational_status": status}

    model = database.create(
        city=1,
        country=1,
        user=True,
        cohort_user=cohort_user,
        syllabus_version=True,
        syllabus_schedule=True,
        syllabus={"name": fake.name()},
        survey_template=survey_template,
    )

    certificate = model.syllabus.name
    send_question(model["user"])

    expected = [
        get_serializer(
            {
                "cohort_id": 1,
                "highest": "very good",
                "id": 1,
                "lang": "en",
                "lowest": "not good",
                "status": "SENT",
                "title": f"How has your experience been studying {certificate} so far?",
                "token_id": 1,
                "user_id": 1,
            }
        ),
    ]

    dicts = database.list_of("feedback.Answer")
    assert dicts == expected
    assert len(database.list_of("authenticate.Token")) == 1

    answer = Answer.objects.get(user=model["user"])
    token = answer.token

    params = [model.syllabus.name]
    assert notify_actions.send_email_message.call_args_list == [
        get_email_call("en", "cohort", params, model["user"], model["cohort"].academy, token)
    ]
    assert notify_actions.send_slack.call_args_list == []


# """
# 🔽🔽🔽 Answer are generate and send in a email, passing cohort
# """


@pytest.mark.parametrize(
    "survey_template",
    [
        [
            {"lang": "en", "is_shared": True, "when_asking_cohort": get_translations("en", "cohort")},
            {"lang": "es", "is_shared": True, "when_asking_cohort": get_translations("es", "cohort"), "original_id": 1},
        ],
    ],
)
@pytest.mark.parametrize("status", ["ACTIVE", "GRADUATED"])
def test_send_question__just_send_by_email__passing_cohort(
    database: capy.Database, fake: capy.Fake, status: str, survey_template: list[dict]
):
    cohort_user = {"educational_status": status}

    model = database.create(
        city=1,
        country=1,
        user=True,
        cohort_user=cohort_user,
        syllabus_version=True,
        syllabus_schedule=True,
        syllabus={"name": fake.name()},
        survey_template=survey_template,
    )

    certificate = model.syllabus.name
    send_question(model.user, model.cohort)

    expected = [
        get_serializer(
            {
                "cohort_id": 1,
                "highest": "very good",
                "id": 1,
                "lang": "en",
                "lowest": "not good",
                "status": "SENT",
                "title": f"How has your experience been studying {certificate} so far?",
                "token_id": 1,
                "user_id": 1,
            }
        ),
    ]

    dicts = database.list_of("feedback.Answer")
    assert dicts == expected
    assert len(database.list_of("authenticate.Token")) == 1

    answer = Answer.objects.get(user=model["user"])
    token = answer.token

    params = [model.syllabus.name]
    assert notify_actions.send_email_message.call_args_list == [
        get_email_call("en", "cohort", params, model["user"], model["cohort"].academy, token)
    ]
    assert notify_actions.send_slack.call_args_list == []


# """
# 🔽🔽🔽 Answer are generate and send in a email and slack
# """


@pytest.mark.parametrize(
    "survey_template",
    [
        [
            {"lang": "en", "is_shared": True, "when_asking_cohort": get_translations("en", "cohort")},
            {"lang": "es", "is_shared": True, "when_asking_cohort": get_translations("es", "cohort"), "original_id": 1},
        ],
    ],
)
@pytest.mark.parametrize("status", ["ACTIVE", "GRADUATED"])
def test_send_question__send_by_email_and_slack(
    database: capy.Database, fake: capy.Fake, status: str, survey_template: list[dict]
):
    cohort_user = {"educational_status": status}

    cohort_kwargs = {"language": "en"}
    model = database.create(
        city=1,
        country=1,
        user=True,
        cohort_user=cohort_user,
        slack_user=True,
        slack_team=True,
        credentials_slack=True,
        academy=True,
        syllabus_version=True,
        syllabus_schedule=True,
        cohort=cohort_kwargs,
        syllabus={"name": fake.name()},
        survey_template=survey_template,
    )

    certificate = model.syllabus.name
    send_question(model["user"])

    expected = [
        get_serializer(
            {
                "id": 1,
                "title": f"How has your experience been studying {certificate} so far?",
                "lowest": "not good",
                "highest": "very good",
                "lang": "en",
                "cohort_id": 1,
                "token_id": 1,
                "status": "SENT",
                "user_id": 1,
            }
        ),
    ]

    dicts = [answer for answer in database.list_of("feedback.Answer")]
    assert dicts == expected
    assert len(database.list_of("authenticate.Token")) == 1

    answer = Answer.objects.get(user=model["user"])
    token = answer.token

    params = [model.syllabus.name]
    assert notify_actions.send_email_message.call_args_list == [
        get_email_call("en", "cohort", params, model["user"], model["cohort"].academy, token)
    ]
    assert notify_actions.send_slack.call_args_list == [
        get_slack_call("en", "cohort", params, model["slack_user"], model["slack_team"], model["academy"], token)
    ]


# """
# 🔽🔽🔽 Send question in english
# """


@pytest.mark.parametrize(
    "survey_template",
    [
        [
            {"lang": "en", "is_shared": True, "when_asking_cohort": get_translations("en", "cohort")},
            {"lang": "es", "is_shared": True, "when_asking_cohort": get_translations("es", "cohort"), "original_id": 1},
        ],
    ],
)
@pytest.mark.parametrize("status", ["ACTIVE", "GRADUATED"])
def test_send_question__with_cohort_lang_en(
    database: capy.Database, fake: capy.Fake, status: str, survey_template: list[dict]
):
    cohort_user = {"educational_status": status}

    cohort_kwargs = {"language": "en"}
    model = database.create(
        city=1,
        country=1,
        user=True,
        cohort_user=cohort_user,
        slack_user=True,
        slack_team=True,
        credentials_slack=True,
        academy=True,
        syllabus_version=True,
        syllabus_schedule=True,
        cohort=cohort_kwargs,
        syllabus={"name": fake.name()},
        survey_template=survey_template,
    )

    certificate = model.syllabus.name
    send_question(model["user"])

    expected = [
        get_serializer(
            {
                "id": 1,
                "title": f"How has your experience been studying {certificate} so far?",
                "lowest": "not good",
                "highest": "very good",
                "lang": "en",
                "cohort_id": 1,
                "token_id": 1,
                "status": "SENT",
                "user_id": 1,
            }
        ),
    ]

    dicts = database.list_of("feedback.Answer")
    assert dicts == expected
    assert len(database.list_of("authenticate.Token")) == 1

    answer = Answer.objects.get(user=model["user"])
    token = answer.token

    params = [model.syllabus.name]
    assert notify_actions.send_email_message.call_args_list == [
        get_email_call("en", "cohort", params, model["user"], model["cohort"].academy, token)
    ]
    assert notify_actions.send_slack.call_args_list == [
        get_slack_call("en", "cohort", params, model["slack_user"], model["slack_team"], model["academy"], token)
    ]


# """
# 🔽🔽🔽 Send question in spanish
# """


@pytest.mark.parametrize(
    "survey_template",
    [
        [
            {"lang": "en", "is_shared": True, "when_asking_cohort": get_translations("en", "cohort")},
            {"lang": "es", "is_shared": True, "when_asking_cohort": get_translations("es", "cohort"), "original_id": 1},
        ],
    ],
)
@pytest.mark.parametrize("status", ["ACTIVE", "GRADUATED"])
def test_send_question__with_cohort_lang_es(
    database: capy.Database, fake: capy.Fake, status: str, survey_template: list[dict]
):
    cohort_user = {"educational_status": status}

    cohort_kwargs = {"language": "es"}
    model = database.create(
        city=1,
        country=1,
        user=True,
        cohort_user=cohort_user,
        slack_user=True,
        slack_team=True,
        credentials_slack=True,
        academy=True,
        syllabus_version=True,
        syllabus_schedule=True,
        cohort=cohort_kwargs,
        syllabus={"name": fake.name()},
        survey_template=survey_template,
    )

    certificate = model.syllabus.name
    send_question(model["user"])

    expected = [
        get_serializer(
            {
                "cohort_id": 1,
                "highest": "muy buena",
                "id": 1,
                "lang": "es",
                "lowest": "mala",
                "status": "SENT",
                "title": f"¿Cómo ha sido tu experiencia estudiando {certificate} hasta este momento?",
                "token_id": 1,
                "user_id": 1,
            }
        ),
    ]

    dicts = database.list_of("feedback.Answer")
    assert dicts == expected
    assert len(database.list_of("authenticate.Token")) == 1

    answer = Answer.objects.get(user=model["user"])
    token = answer.token

    params = [model.syllabus.name]
    assert notify_actions.send_email_message.call_args_list == [
        get_email_call("es", "cohort", params, model["user"], model["cohort"].academy, token)
    ]
    assert notify_actions.send_slack.call_args_list == [
        get_slack_call("es", "cohort", params, model["slack_user"], model["slack_team"], model["academy"], token)
    ]
