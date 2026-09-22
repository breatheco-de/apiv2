import pytest

from breathecode.assignments.models import Task
from breathecode.assignments.serializers import TaskStatusUpdatedHookSerializer
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

MODULE_JSON = {
    "days": [
        {
            "id": 1,
            "label": "Module 1",
            "lessons": [{"slug": "lesson-1", "title": "Lesson 1"}],
            "quizzes": [],
            "replits": [{"slug": "exercise-1", "title": "Exercise 1"}],
            "assignments": [],
        }
    ]
}


def _task(model, slug, task_type, task_status="DONE", revision_status="PENDING"):
    return Task.objects.create(
        user=model.user,
        cohort=model.cohort,
        associated_slug=slug,
        title=slug,
        task_type=task_type,
        task_status=task_status,
        revision_status=revision_status,
        description="",
    )


@pytest.fixture
def cohort_with_module(db, bc: Breathecode):
    return bc.database.create(
        user=1,
        cohort=1,
        syllabus_version={"json": MODULE_JSON},
    )


@pytest.mark.django_db
def test_module_completed_is_false_when_task_is_not_done(cohort_with_module):
    task = _task(cohort_with_module, "lesson-1", "LESSON", task_status="PENDING")

    payload = TaskStatusUpdatedHookSerializer(task).data

    assert payload["module_completed"] is False
    assert payload["completed_module_name"] is None
    assert payload["macro_cohort"] is None
    assert payload["plan_slugs"] == []


@pytest.mark.django_db
def test_module_completed_is_false_when_another_asset_is_pending(cohort_with_module):
    task = _task(cohort_with_module, "lesson-1", "LESSON")

    assert TaskStatusUpdatedHookSerializer(task).data["module_completed"] is False


@pytest.mark.django_db
def test_module_completed_is_true_when_every_asset_in_the_module_is_done(cohort_with_module):
    _task(cohort_with_module, "exercise-1", "EXERCISE")
    task = _task(cohort_with_module, "lesson-1", "LESSON")

    payload = TaskStatusUpdatedHookSerializer(task).data

    assert payload["module_completed"] is True
    assert payload["completed_module_name"] == "Module 1"


@pytest.mark.django_db
def test_completed_module_name_uses_english_then_spanish(db, bc: Breathecode):
    model = _cohort(
        bc,
        {
            "days": [
                {
                    "label": {"en": "Intro", "es": "Introducción"},
                    "lessons": [{"slug": "lesson-1"}],
                }
            ]
        },
    )
    task = _task(model, "lesson-1", "LESSON")

    assert TaskStatusUpdatedHookSerializer(task).data["completed_module_name"] == "Intro"


@pytest.mark.django_db
def test_completed_module_name_falls_back_to_spanish(db, bc: Breathecode):
    model = _cohort(
        bc,
        {
            "days": [
                {
                    "label": {"es": "Introducción"},
                    "lessons": [{"slug": "lesson-1"}],
                }
            ]
        },
    )
    task = _task(model, "lesson-1", "LESSON")

    assert TaskStatusUpdatedHookSerializer(task).data["completed_module_name"] == "Introducción"


@pytest.mark.django_db
@pytest.mark.django_db
def test_macro_cohort_comes_from_source_macro_and_plan_slugs_are_current(db, bc: Breathecode):
    from datetime import timedelta

    from django.utils import timezone

    from breathecode.admissions.models import Cohort

    later = timezone.now() + timedelta(days=30)
    model = bc.database.create(
        user=1,
        academy=1,
        cohort=1,
        cohort_user=1,
        plan=[
            {"slug": "live-sub", "is_renewable": True, "time_of_life": 1, "time_of_life_unit": "MONTH"},
            {"slug": "live-financing", "is_renewable": False, "time_of_life": 1, "time_of_life_unit": "MONTH"},
            {"slug": "cancelled-plan", "is_renewable": True, "time_of_life": 1, "time_of_life_unit": "MONTH"},
        ],
        subscription=[
            {"status": "ACTIVE", "next_payment_at": later, "valid_until": later},
            {"status": "CANCELLED", "next_payment_at": later, "valid_until": later},
        ],
        plan_financing={
            "status": "FULLY_PAID",
            "next_payment_at": later,
            "valid_until": later,
            "monthly_price": 10,
            "how_many_installments": 1,
            "installments_paid": 1,
            "plan_expires_at": later,
        },
    )
    macro = Cohort.objects.create(
        slug="macro-course",
        name="Macro Course",
        kickoff_date=timezone.now(),
        academy=model.academy,
    )
    model.cohort_user.source_macro_cohort = macro
    model.cohort_user.save(update_fields=["source_macro_cohort"])

    live_sub, live_financing, cancelled = model.plan
    active, dropped = model.subscription
    active.plans.set([live_sub])
    dropped.plans.set([cancelled])
    model.plan_financing.plans.set([live_financing])

    payload = TaskStatusUpdatedHookSerializer(_task(model, "lesson-1", "LESSON")).data

    assert payload["macro_cohort"] == {"id": macro.id, "name": "Macro Course", "slug": "macro-course"}
    assert payload["plan_slugs"] == ["live-financing", "live-sub"]


def _parent(academy, slug, name):
    from django.utils import timezone

    from breathecode.admissions.models import Cohort

    return Cohort.objects.create(slug=slug, name=name, kickoff_date=timezone.now(), academy=academy)


@pytest.mark.django_db
def test_macro_cohort_uses_the_only_enrolled_parent(db, bc: Breathecode):
    from breathecode.admissions.models import CohortUser

    model = bc.database.create(user=1, academy=1, cohort=1, cohort_user=1)
    parent = _parent(model.academy, "ai-engineering-1", "AI Engineering 1")
    other = _parent(model.academy, "miami-ai-engineering-2", "Miami AI Engineering 2")
    parent.micro_cohorts.add(model.cohort)
    other.micro_cohorts.add(model.cohort)
    CohortUser.objects.create(user=model.user, cohort=parent, role="STUDENT")

    payload = TaskStatusUpdatedHookSerializer(_task(model, "lesson-1", "LESSON")).data

    assert payload["macro_cohort"] == {"id": parent.id, "name": "AI Engineering 1", "slug": "ai-engineering-1"}


@pytest.mark.django_db
def test_macro_cohort_stays_null_when_several_parents_are_enrolled(db, bc: Breathecode):
    from breathecode.admissions.models import CohortUser

    model = bc.database.create(user=1, academy=1, cohort=1, cohort_user=1)
    parent = _parent(model.academy, "ai-engineering-1", "AI Engineering 1")
    other = _parent(model.academy, "miami-ai-engineering-2", "Miami AI Engineering 2")
    parent.micro_cohorts.add(model.cohort)
    other.micro_cohorts.add(model.cohort)
    CohortUser.objects.create(user=model.user, cohort=parent, role="STUDENT")
    CohortUser.objects.create(user=model.user, cohort=other, role="STUDENT")

    payload = TaskStatusUpdatedHookSerializer(_task(model, "lesson-1", "LESSON")).data

    assert payload["macro_cohort"] is None


@pytest.mark.django_db
def test_module_completed_is_false_when_the_asset_is_not_in_the_syllabus(cohort_with_module):
    task = _task(cohort_with_module, "unknown-asset", "LESSON")

    assert TaskStatusUpdatedHookSerializer(task).data["module_completed"] is False


def _cohort(bc, syllabus_json):
    return bc.database.create(
        user=1,
        cohort=1,
        syllabus_version={"json": syllabus_json},
    )


@pytest.mark.django_db
def test_syllabus_completed_is_true_when_the_last_asset_is_done(db, bc: Breathecode):
    model = _cohort(
        bc,
        {
            "days": [
                {"lessons": [{"slug": "lesson-1"}]},
                {"assignments": [{"slug": "project-1", "mandatory": True}]},
            ]
        },
    )
    _task(model, "lesson-1", "LESSON")
    task = _task(model, "project-1", "PROJECT", revision_status="PENDING")

    payload = TaskStatusUpdatedHookSerializer(task).data

    assert payload["syllabus_completed"] is True
    assert payload["module_completed"] is True


@pytest.mark.django_db
def test_syllabus_completed_is_false_when_another_asset_is_pending(db, bc: Breathecode):
    model = _cohort(
        bc,
        {
            "days": [
                {
                    "lessons": [{"slug": "lesson-1"}],
                    "assignments": [{"slug": "project-1"}],
                }
            ]
        },
    )
    task = _task(model, "project-1", "PROJECT")

    payload = TaskStatusUpdatedHookSerializer(task).data

    assert payload["syllabus_completed"] is False
    assert payload["module_completed"] is False
