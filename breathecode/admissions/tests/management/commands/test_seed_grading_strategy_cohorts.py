from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command

from breathecode.admissions.models import Cohort, CohortUser, Syllabus
from breathecode.payments.models import CohortSet, Plan, PlanFinancing


@patch("breathecode.registry.tasks.async_add_syllabus_translations.delay")
def test_seed_grading_strategy_cohorts(delay_mock, db):
    out = StringIO()

    call_command("seed_grading_strategy_cohorts", "--clear", stdout=out)

    assert Cohort.objects.filter(slug__startswith="grading-strategy-demo").count() == 5
    assert Syllabus.objects.filter(slug__startswith="grading-strategy-demo").count() == 5
    assert (
        Syllabus.objects.filter(
            slug="grading-strategy-demo-partial-lessons-quizzes",
            syllabusversion__json__grading_strategy__completion__type="PARTIAL_COMPLETION",
        ).count()
        == 1
    )
    assert CohortSet.objects.filter(slug="grading-strategy-demo-cohort-set").count() == 1
    assert (
        Plan.objects.filter(slug="grading-strategy-demo-plan", cohort_set__slug="grading-strategy-demo-cohort-set").count()
        == 1
    )
    assert delay_mock.call_args_list == []


@patch("breathecode.registry.tasks.async_add_syllabus_translations.delay")
def test_seed_grading_strategy_cohorts_with_user(delay_mock, db):
    out = StringIO()
    user = User.objects.create_user(username="demo-user", email="demo@example.com")

    call_command("seed_grading_strategy_cohorts", "--clear", "--user", "demo@example.com", stdout=out)

    cohorts = Cohort.objects.filter(slug__startswith="grading-strategy-demo")
    assert CohortUser.objects.filter(user=user, cohort__in=cohorts, role="STUDENT").count() == 5
    financing = PlanFinancing.objects.filter(user=user, selected_cohort_set__slug="grading-strategy-demo-cohort-set").first()
    assert financing is not None
    assert financing.plans.filter(slug="grading-strategy-demo-plan").count() == 1
    assert financing.joined_cohorts.count() == 5
    assert delay_mock.call_args_list == []
