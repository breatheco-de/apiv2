from io import StringIO
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command

from breathecode.admissions.models import Academy, City, Country, Cohort, CohortUser, Syllabus, SyllabusVersion
from breathecode.payments.models import CohortSet, Currency, Plan, PlanFinancing
from breathecode.registry.models import Asset


@pytest.fixture
def seed_prerequisites(db):
    country = Country.objects.create(code="US", name="United States")
    city = City.objects.create(name="Miami", country=country)
    currency = Currency.objects.create(code="USD", name="US Dollar", decimals=2)
    country.currencies.add(currency)
    Academy.objects.create(
        id=47,
        slug="academy-47",
        name="Academy 47",
        logo_url="https://example.com/logo.png",
        street_address="Demo street",
        city=city,
        country=country,
        main_currency=currency,
        available_as_saas=True,
    )
    User.objects.create_user(id=1, username="teacher", email="teacher@example.com")
    Asset.objects.create(slug="intro-to-numpy", title="Introduction to Numpy", asset_type="LESSON", status="PUBLISHED")
    Asset.objects.create(
        slug="numpy-exercises-tutorial", title="Numpy Tutorial Exercises", asset_type="EXERCISE", status="PUBLISHED"
    )
    Asset.objects.create(slug="demo-quiz", title="Demo Quiz", asset_type="QUIZ", status="PUBLISHED")
    Asset.objects.create(slug="demo-project", title="Demo Project", asset_type="PROJECT", status="PUBLISHED")


@patch("breathecode.registry.tasks.async_add_syllabus_translations.delay")
def test_seed_grading_strategy_cohorts(delay_mock, seed_prerequisites):
    out = StringIO()

    call_command("seed_grading_strategy_cohorts", "--clear", stdout=out)

    assert Cohort.objects.filter(slug__startswith="grading-strategy-demo", academy_id=47).count() == 6
    macro = Cohort.objects.get(slug="grading-strategy-demo-macro")
    assert macro.micro_cohorts.count() == 5
    assert macro.cohorts_order
    assert macro.syllabus_version is not None
    assert CohortUser.objects.filter(user_id=1, role="TEACHER", cohort=macro).exists()
    assert Syllabus.objects.filter(slug__startswith="grading-strategy-demo", academy_owner_id=47).count() == 6
    assert (
        Syllabus.objects.filter(
            slug="grading-strategy-demo-partial-lessons-quizzes",
            syllabusversion__json__grading_strategy__completion__type="PARTIAL_COMPLETION",
        ).count()
        == 1
    )
    full_syllabus = SyllabusVersion.objects.get(syllabus__slug="grading-strategy-demo-full", version=1)
    for day in full_syllabus.json["days"]:
        assert "lessons" in day
        assert "replits" in day
        assert "quizzes" in day
        assert "assignments" in day
        assert isinstance(day["label"], dict)
    assert full_syllabus.json["days"][0]["lessons"][0]["slug"] == "intro-to-numpy"
    assert CohortUser.objects.filter(user_id=1, role="TEACHER", cohort__slug="grading-strategy-demo-full").exists()
    assert CohortSet.objects.filter(slug="grading-strategy-demo-cohort-set").count() == 1
    assert (
        Plan.objects.filter(slug="grading-strategy-demo-plan", cohort_set__slug="grading-strategy-demo-cohort-set").count()
        == 1
    )
    assert delay_mock.call_args_list == []


@patch("breathecode.registry.tasks.async_add_syllabus_translations.delay")
def test_seed_grading_strategy_cohorts_with_user(delay_mock, seed_prerequisites):
    out = StringIO()
    user = User.objects.create_user(username="demo-user", email="demo@example.com")

    call_command("seed_grading_strategy_cohorts", "--clear", "--user", "demo@example.com", stdout=out)

    cohorts = Cohort.objects.filter(slug__startswith="grading-strategy-demo")
    assert CohortUser.objects.filter(user=user, cohort__in=cohorts, role="STUDENT").count() == 6
    financing = PlanFinancing.objects.filter(user=user, selected_cohort_set__slug="grading-strategy-demo-cohort-set").first()
    assert financing is not None
    assert financing.plans.filter(slug="grading-strategy-demo-plan").count() == 1
    assert financing.joined_cohorts.count() == 6
    assert delay_mock.call_args_list == []
