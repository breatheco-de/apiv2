"""
Test /academy/survey
"""

from unittest.mock import MagicMock, patch

import pytest
from capyc import pytest as capy
from capyc.rest_framework.exceptions import ValidationException
from django.utils import timezone

from breathecode.feedback.tasks import generate_user_cohort_survey_answers

from ...actions import strings

UTC_NOW = timezone.now()


def get_translations(lang, template):
    return {
        "title": strings[lang][template]["title"],
        "highest": strings[lang][template]["highest"],
        "lowest": strings[lang][template]["lowest"],
        "survey_subject": strings[lang][template]["survey_subject"],
    }


@pytest.fixture(autouse=True)
def setup(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None)
    )
    monkeypatch.setattr("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))


def answer(data={}):
    return {
        "academy_id": 0,
        "cohort_id": 0,
        "comment": None,
        "event_id": None,
        "highest": "very good",
        "id": 0,
        "lang": "en",
        "lowest": "not good",
        "mentor_id": None,
        "mentorship_session_id": None,
        "opened_at": UTC_NOW,
        "score": None,
        "sent_at": None,
        "status": "OPENED",
        "survey_id": 0,
        "title": "",
        "token_id": None,
        "user_id": 0,
        "question_by_slug": None,
        "asset_id": None,
        "live_class_id": None,
        **data,
    }


def test_when_student_is_not_assigned(database: capy.Database):

    model = database.create(city=1, country=1, cohort=1, user=1, survey=1)

    with pytest.raises(ValidationException, match="This student does not belong to this cohort"):
        generate_user_cohort_survey_answers(model.user, model.survey, status="OPENED")

    assert database.list_of("feedback.Answer") == []


@pytest.mark.parametrize("status", ["ACTIVE", "GRADUATED"])
def test_when_teacher_is_not_assigned(database: capy.Database, status: str):
    cohort_user = {"educational_status": status}

    model = database.create(city=1, country=1, cohort=1, user=1, survey=1, cohort_user=cohort_user)

    with pytest.raises(ValidationException, match="This cohort must have a teacher assigned to be able to survey it"):
        generate_user_cohort_survey_answers(model.user, model.survey, status="OPENED")

    assert database.list_of("feedback.Answer") == []


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
def test_when_teacher_is_assigned(database: capy.Database, survey_template: list[dict], status: str):
    cohort_users = [{"educational_status": status}, {"role": "TEACHER", "educational_status": status}]

    model = database.create(
        city=1, country=1, cohort=1, user=1, survey=1, cohort_user=cohort_users, survey_template=survey_template
    )

    generate_user_cohort_survey_answers(model.user, model.survey, status="OPENED")

    answers = [
        {
            "title": f"How has your experience been studying {model.cohort.name} so far?",
            "lowest": "not good",
            "highest": "very good",
            "cohort_id": 1,
            "academy_id": 1,
            "token_id": None,
            "asset_id": None,
            "live_class_id": None,
        },
        {
            "title": f"How has your experience been with your mentor {model.user.first_name} {model.user.last_name} so far?",
            "lang": "en",
            "mentor_id": 1,
            "lowest": "not good",
            "mentorship_session_id": None,
            "score": None,
            "sent_at": None,
            "status": "OPENED",
            "highest": "very good",
            "cohort_id": 1,
            "academy_id": 1,
        },
        {
            "title": f"How likely are you to recommend {model.academy.name} to your friends " "and family?",
            "lowest": "not likely",
            "highest": "very likely",
            "cohort_id": None,
            "academy_id": 1,
        },
        {
            "title": f"How has your experience been with the platform and content so far?",
            "lowest": "not good",
            "highest": "very good",
            "cohort_id": None,
            "academy_id": None,
            "question_by_slug": "PLATFORM",
        },
    ]

    assert database.list_of("feedback.Answer") == [
        answer(
            {
                "id": index + 1,
                "user_id": 1,
                "survey_id": 1,
                **elem,
            }
        )
        for index, elem in enumerate(answers)
    ]


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
def test_when_cohort_has_syllabus(database: capy.Database, survey_template: list[dict], status: str):
    cohort_users = [{"educational_status": status}, {"role": "TEACHER", "educational_status": status}]

    model = database.create(
        city=1,
        country=1,
        cohort=1,
        user=1,
        survey=1,
        cohort_user=cohort_users,
        syllabus_version=1,
        survey_template=survey_template,
    )

    generate_user_cohort_survey_answers(model.user, model.survey, status="OPENED")

    answers = [
        {
            "title": f"How has your experience been studying {model.cohort.name} so far?",
            "lowest": "not good",
            "cohort_id": 1,
            "academy_id": 1,
            "highest": "very good",
            "token_id": None,
        },
        {
            "title": f"How has your experience been with your mentor {model.user.first_name} {model.user.last_name} so far?",
            "lang": "en",
            "mentor_id": 1,
            "cohort_id": 1,
            "academy_id": 1,
            "lowest": "not good",
            "mentorship_session_id": None,
            "score": None,
            "sent_at": None,
            "status": "OPENED",
            "highest": "very good",
        },
        {
            "title": f"How likely are you to recommend {model.academy.name} to your friends " "and family?",
            "academy_id": 1,
            "lowest": "not likely",
            "highest": "very likely",
            "cohort_id": None,
        },
        {
            "title": f"How has your experience been with the platform and content so far?",
            "lowest": "not good",
            "highest": "very good",
            "cohort_id": None,
            "academy_id": None,
            "question_by_slug": "PLATFORM",
        },
    ]
    assert database.list_of("feedback.Answer") == [
        answer(
            {
                "id": index + 1,
                "user_id": 1,
                "survey_id": 1,
                **elem,
            }
        )
        for index, elem in enumerate(answers)
    ]


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
def test_when_cohort_is_available_as_saas(database: capy.Database, survey_template: list[dict], status: str):
    cohort_users = [{"educational_status": status}, {"role": "TEACHER", "educational_status": status}]

    model = database.create(
        city=1,
        country=1,
        cohort={"available_as_saas": True},
        user=1,
        survey=1,
        cohort_user=cohort_users,
        syllabus_version=1,
        survey_template=survey_template,
    )

    generate_user_cohort_survey_answers(model.user, model.survey, status="OPENED")

    answers = [
        {
            "title": f"How has your experience been studying {model.cohort.name} so far?",
            "lowest": "not good",
            "cohort_id": 1,
            "academy_id": 1,
            "highest": "very good",
            "token_id": None,
        },
        {
            "title": f"How likely are you to recommend {model.academy.name} to your friends " "and family?",
            "academy_id": 1,
            "lowest": "not likely",
            "highest": "very likely",
            "cohort_id": None,
        },
        {
            "title": f"How has your experience been with the platform and content so far?",
            "lowest": "not good",
            "highest": "very good",
            "cohort_id": None,
            "academy_id": None,
            "question_by_slug": "PLATFORM",
        },
    ]
    assert database.list_of("feedback.Answer") == [
        answer(
            {
                "id": index + 1,
                "user_id": 1,
                "survey_id": 1,
                **elem,
            }
        )
        for index, elem in enumerate(answers)
    ]


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
def test_role_assistant(database: capy.Database, survey_template: list[dict], status: str):
    cohort_users = [
        {"role": "TEACHER", "educational_status": status},
        {"role": "ASSISTANT", "educational_status": status},
        {"educational_status": status},
    ]

    model = database.create(
        city=1, country=1, cohort=1, user=1, survey=1, cohort_user=cohort_users, survey_template=survey_template
    )

    generate_user_cohort_survey_answers(model.user, model.survey, status="OPENED")

    answers = [
        {
            "title": f"How has your experience been studying {model.cohort.name} so far?",
            "lowest": "not good",
            "highest": "very good",
            "cohort_id": 1,
            "academy_id": 1,
            "token_id": None,
        },
        {
            "title": f"How has your experience been with your mentor {model.user.first_name} {model.user.last_name} so far?",
            "lang": "en",
            "mentor_id": 1,
            "lowest": "not good",
            "mentorship_session_id": None,
            "score": None,
            "sent_at": None,
            "status": "OPENED",
            "highest": "very good",
            "cohort_id": 1,
            "academy_id": 1,
        },
        {
            "title": f"How has your experience been with your mentor {model.user.first_name} {model.user.last_name} so far?",
            "lowest": "not good",
            "highest": "very good",
            "cohort_id": 1,
            "academy_id": 1,
            "mentor_id": 1,
        },
        {
            "title": f"How likely are you to recommend {model.academy.name} to your friends " "and family?",
            "lowest": "not likely",
            "highest": "very likely",
            "cohort_id": None,
            "academy_id": 1,
        },
        {
            "title": f"How has your experience been with the platform and content so far?",
            "lowest": "not good",
            "highest": "very good",
            "cohort_id": None,
            "academy_id": None,
            "question_by_slug": "PLATFORM",
        },
    ]

    assert database.list_of("feedback.Answer") == [
        answer(
            {
                "id": index + 1,
                "user_id": 1,
                "survey_id": 1,
                **elem,
            }
        )
        for index, elem in enumerate(answers)
    ]
