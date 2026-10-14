"""
End to end flow of a student through macro cohorts that share micro cohorts.

Enroll in a macro -> get the micro enrollments -> create the tasks the syllabus shows -> complete them ->
graduate from the micro -> graduate from the macro.
"""

from unittest.mock import patch

import capyc.pytest as capy
import pytest
from django.urls import reverse_lazy
from rest_framework import status

from breathecode.admissions.actions import resolve_syllabus_json
from breathecode.admissions.models import CohortUser
from breathecode.assignments.models import AssignmentTelemetry, Task
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

TASK_URL = reverse_lazy("assignments:user_me_task")
BOTH_PROJECTS = ["project-common", "project-extra"]
SYLLABUS_KEYS = {"PROJECT": "assignments", "EXERCISE": "replits", "LESSON": "lessons", "QUIZ": "quizzes"}


def _asset(slug):
    return {"slug": slug, "title": slug, "mandatory": True}


def create_micro(bc: Breathecode, slug="micro-course", days=None, version=1):
    """
    A micro cohort. `days` is a list of {"assignments": [...slugs], "replits": [...slugs]}.

    By default it has no projects of its own, every macro adds them, like the real AI Engineering micros.
    """
    days = days if days is not None else [{"replits": ["exercise-common"]}]
    json_days = []
    for index, day in enumerate(days):
        json_days.append(
            {
                "id": index + 1,
                "label": f"Day {index + 1}",
                "lessons": [],
                "quizzes": [],
                "replits": [_asset(slug) for slug in day.get("replits", [])],
                "assignments": [_asset(slug) for slug in day.get("assignments", [])],
            }
        )
    return bc.database.create(
        syllabus={"slug": slug},
        syllabus_version={"version": version, "json": {"days": json_days}},
        cohort={"slug": f"{slug}-cohort-v{version}", "available_as_saas": True},
    )


def create_macro(bc: Breathecode, slug, micros, overrides=None):
    """
    A macro cohort. `overrides` maps a micro syllabus slug to its override days, e.g.
    {"micro-course": [{"assignments": [None, "project-extra"]}]}; None keeps the base asset, "DELETED" drops it.
    """
    macro_json = {"days": []}
    for micro_slug, override_days in (overrides or {}).items():
        micro = next(m for m in micros if m.syllabus.slug == micro_slug)
        days = []
        for day in override_days:
            override_day = {}
            for key in ("assignments", "replits"):
                if key not in day:
                    continue
                override_day[key] = [
                    None if item is None else {"status": "DELETED"} if item == "DELETED" else _asset(item)
                    for item in day[key]
                ]
            days.append(override_day)
        macro_json[f"{micro_slug}.v{micro.syllabus_version.version}"] = {"days": days}

    return bc.database.create(
        syllabus={"slug": f"{slug}-course"},
        syllabus_version={"version": 1, "json": macro_json},
        cohort={"slug": slug, "available_as_saas": True, "micro_cohorts": [m.cohort for m in micros]},
    )


def enroll(bc: Breathecode, user, macro):
    """Enroll through the real path: the cohort_user_created signal joins the student to the micros."""
    return bc.database.create(cohort_user={"user": user, "cohort": macro.cohort, "role": "STUDENT"}).cohort_user


def micro_enrollment(user, micro):
    return CohortUser.objects.get(user=user, cohort=micro.cohort)


def visible_assets(micro, macro):
    """What the syllabus endpoint returns for this micro when it is opened through this macro."""
    syllabus = resolve_syllabus_json(
        micro.syllabus_version.json,
        macro_syllabus_json=macro.syllabus_version.json,
        syllabus_slug=micro.syllabus.slug,
        syllabus_version=micro.syllabus_version.version,
    )
    assets = []
    for day in syllabus.get("days", []):
        for task_type, key in SYLLABUS_KEYS.items():
            for asset in day.get(key, []):
                if isinstance(asset, dict) and asset.get("slug"):
                    assets.append((task_type, asset["slug"]))
    return assets


def open_micro(client: capy.Client, user, micro, macro, send_macro=True):
    """The frontend opens the micro through a macro and asks the tasks of everything it shows."""
    client.force_authenticate(user)
    assets = visible_assets(micro, macro)
    url = TASK_URL + (f"?macro-cohort={macro.cohort.slug}" if send_macro else "")
    response = client.post(
        url,
        [
            {"associated_slug": slug, "title": slug, "task_type": task_type, "cohort": micro.cohort.id}
            for task_type, slug in assets
        ],
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    return assets


def micro_tasks(user, micro):
    return {task.associated_slug: task for task in Task.objects.filter(user=user, cohort=micro.cohort)}


def approve(user, micro, slug):
    task = Task.objects.get(user=user, cohort=micro.cohort, associated_slug=slug)
    task.task_status = "DONE"
    task.revision_status = "APPROVED"
    task.save()


def approve_everything(user, micro):
    for slug in micro_tasks(user, micro):
        approve(user, micro, slug)


def edu_status(user, cohort_model):
    return CohortUser.objects.get(user=user, cohort=cohort_model.cohort).educational_status


@pytest.fixture(autouse=True)
def setup(db, enable_signals):
    enable_signals()
    yield


@pytest.fixture
def student(bc: Breathecode):
    return bc.database.create(user=1).user


# -- one macro ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("send_macro", [True, False])
def test_one_macro__full_flow_graduates_micro_and_macro(client, bc, student, send_macro):
    micro = create_micro(bc)
    macro = create_macro(bc, "macro-a", [micro], {"micro-course": [{"assignments": BOTH_PROJECTS}]})

    enroll(bc, student, macro)
    assert micro_enrollment(student, micro).source_macro_cohort_id == macro.cohort.id

    assets = open_micro(client, student, micro, macro, send_macro=send_macro)
    assert sorted(micro_tasks(student, micro)) == sorted(slug for _, slug in assets)
    assert "project-extra" in micro_tasks(student, micro)

    approve(student, micro, "project-common")
    assert edu_status(student, micro) == "ACTIVE"

    approve(student, micro, "project-extra")
    assert edu_status(student, micro) == "GRADUATED"
    assert edu_status(student, macro) == "GRADUATED"


def test_one_macro__asset_deleted_by_override_gets_no_task(client, bc, student):
    micro = create_micro(bc)
    macro = create_macro(
        bc, "macro-a", [micro], {"micro-course": [{"replits": ["DELETED"], "assignments": ["project-common"]}]}
    )
    enroll(bc, student, macro)

    open_micro(client, student, micro, macro)
    assert sorted(micro_tasks(student, micro)) == ["project-common"]

    # a client asking for it anyway gets nothing
    client.post(
        TASK_URL + "?macro-cohort=macro-a",
        [{"associated_slug": "exercise-common", "title": "x", "task_type": "EXERCISE", "cohort": micro.cohort.id}],
        format="json",
    )
    assert sorted(micro_tasks(student, micro)) == ["project-common"]


def test_one_macro__opening_twice_does_not_duplicate_tasks(client, bc, student):
    micro = create_micro(bc)
    macro = create_macro(bc, "macro-a", [micro], {"micro-course": [{"assignments": BOTH_PROJECTS}]})
    enroll(bc, student, macro)

    open_micro(client, student, micro, macro)
    approve(student, micro, "project-common")
    open_micro(client, student, micro, macro)

    assert Task.objects.filter(user=student, cohort=micro.cohort).count() == 3
    assert micro_tasks(student, micro)["project-common"].revision_status == "APPROVED"


def test_one_macro__student_of_a_micro_without_macro_keeps_legacy_behavior(client, bc, student):
    micro = create_micro(bc, days=[{"assignments": ["project-common"]}])
    bc.database.create(cohort_user={"user": student, "cohort": micro.cohort, "role": "STUDENT"})
    client.force_authenticate(student)

    client.post(
        TASK_URL,
        [{"associated_slug": "project-common", "title": "x", "task_type": "PROJECT", "cohort": micro.cohort.id}],
        format="json",
    )
    approve(student, micro, "project-common")

    assert edu_status(student, micro) == "GRADUATED"


# -- two macros sharing the micro, each one overriding it differently --------------------------------------


def _shared_micro_world(bc):
    """macro-general has the lower id and no extra project, macro-campus adds project-extra (issue 10957)."""
    micro = create_micro(bc)
    general = create_macro(bc, "macro-general", [micro], {"micro-course": [{"assignments": ["project-common"]}]})
    campus = create_macro(bc, "macro-campus", [micro], {"micro-course": [{"assignments": BOTH_PROJECTS}]})
    return micro, general, campus


@pytest.mark.parametrize("send_macro", [True, False])
@pytest.mark.parametrize("source", ["empty", "general", "campus"])
def test_two_macros__task_only_in_one_macro_is_created(client, bc, student, send_macro, source):
    micro, general, campus = _shared_micro_world(bc)
    enroll(bc, student, campus)
    enroll(bc, student, general)
    source_id = {"empty": None, "general": general.cohort.id, "campus": campus.cohort.id}[source]
    CohortUser.objects.filter(user=student, cohort=micro.cohort).update(source_macro_cohort_id=source_id)

    open_micro(client, student, micro, campus, send_macro=send_macro)

    assert sorted(micro_tasks(student, micro)) == ["exercise-common", "project-common", "project-extra"]
    assert CohortUser.objects.filter(user=student, cohort=micro.cohort).count() == 1


def test_two_macros__requested_macro_only_gets_its_own_assets(client, bc, student):
    micro, general, campus = _shared_micro_world(bc)
    enroll(bc, student, campus)
    enroll(bc, student, general)

    open_micro(client, student, micro, general)

    assert sorted(micro_tasks(student, micro)) == ["exercise-common", "project-common"]


def test_two_macros__progress_is_shared_and_only_the_extra_task_is_new(client, bc, student):
    micro, general, campus = _shared_micro_world(bc)
    enroll(bc, student, general)
    open_micro(client, student, micro, general)
    approve(student, micro, "exercise-common")
    done_task_id = micro_tasks(student, micro)["exercise-common"].id

    enroll(bc, student, campus)
    open_micro(client, student, micro, campus)

    tasks = micro_tasks(student, micro)
    assert sorted(tasks) == ["exercise-common", "project-common", "project-extra"]
    assert tasks["exercise-common"].id == done_task_id
    assert tasks["exercise-common"].task_status == "DONE"
    assert tasks["project-extra"].task_status == "PENDING"


def test_two_macros__macro_of_another_student_cannot_be_used_to_create_tasks(client, bc, student):
    micro, general, campus = _shared_micro_world(bc)
    enroll(bc, student, general)
    client.force_authenticate(student)

    client.post(
        TASK_URL + "?macro-cohort=macro-campus",
        [{"associated_slug": "project-extra", "title": "x", "task_type": "PROJECT", "cohort": micro.cohort.id}],
        format="json",
    )

    assert "project-extra" not in micro_tasks(student, micro)


def test_two_macros__source_macro_the_student_left_does_not_block_tasks(client, bc, student):
    micro, general, campus = _shared_micro_world(bc)
    general_enrollment = enroll(bc, student, general)
    enroll(bc, student, campus)
    assert micro_enrollment(student, micro).source_macro_cohort_id == general.cohort.id
    general_enrollment.delete()

    open_micro(client, student, micro, campus, send_macro=False)

    assert "project-extra" in micro_tasks(student, micro)


def test_two_macros__second_enrollment_keeps_one_micro_enrollment_and_its_source(bc, student):
    micro, general, campus = _shared_micro_world(bc)
    enroll(bc, student, general)
    enroll(bc, student, campus)

    assert CohortUser.objects.filter(user=student, cohort=micro.cohort).count() == 1
    assert micro_enrollment(student, micro).source_macro_cohort_id == general.cohort.id


# -- graduation with two macros ----------------------------------------------------------------------------


def test_two_macros__both_macros_graduate_once_every_project_is_approved(client, bc, student):
    micro, general, campus = _shared_micro_world(bc)
    enroll(bc, student, campus)
    enroll(bc, student, general)
    open_micro(client, student, micro, campus)

    approve_everything(student, micro)

    assert edu_status(student, micro) == "GRADUATED"
    assert edu_status(student, campus) == "GRADUATED"
    assert edu_status(student, general) == "GRADUATED"


@pytest.mark.xfail(
    strict=True,
    reason="graduation uses source_macro_cohort even when the student left that macro (issue 10957 follow up)",
)
def test_graduation__student_only_in_campus_is_not_graduated_by_a_macro_they_left(client, bc, student):
    """The micro enrollment still points to a macro the student is no longer in."""
    micro, general, campus = _shared_micro_world(bc)
    general_enrollment = enroll(bc, student, general)
    enroll(bc, student, campus)
    general_enrollment.delete()
    open_micro(client, student, micro, campus)

    approve(student, micro, "project-common")

    # campus, the only macro of the student, still requires project-extra
    assert edu_status(student, micro) == "ACTIVE"
    assert edu_status(student, campus) == "ACTIVE"


@pytest.mark.xfail(
    strict=True,
    reason="graduation guesses one macro for a micro shared by the macros of the student (issue 10957 follow up)",
)
def test_graduation__legacy_student_in_two_macros_needs_the_projects_of_the_macro_they_study(client, bc, student):
    """Jesus: empty source, the lowest id macro requires less than the macro the student works through."""
    micro, general, campus = _shared_micro_world(bc)
    enroll(bc, student, campus)
    enroll(bc, student, general)
    CohortUser.objects.filter(user=student, cohort=micro.cohort).update(source_macro_cohort_id=None)
    open_micro(client, student, micro, campus)

    approve(student, micro, "project-common")

    assert edu_status(student, campus) == "ACTIVE"


# -- macro graduation --------------------------------------------------------------------------------------


def test_macro__does_not_graduate_until_every_micro_is_graduated(client, bc, student):
    first = create_micro(bc, slug="micro-one", days=[{"assignments": ["project-one"]}])
    second = create_micro(bc, slug="micro-two", days=[{"assignments": ["project-two"]}])
    macro = create_macro(
        bc,
        "macro-a",
        [first, second],
        {"micro-one": [{"assignments": [None]}], "micro-two": [{"assignments": [None]}]},
    )
    enroll(bc, student, macro)
    open_micro(client, student, first, macro)
    open_micro(client, student, second, macro)

    approve(student, first, "project-one")
    assert edu_status(student, first) == "GRADUATED"
    assert edu_status(student, macro) == "ACTIVE"

    approve(student, second, "project-two")
    assert edu_status(student, macro) == "GRADUATED"


@pytest.mark.xfail(strict=True, reason="macro graduation only looks at the micro enrollments the student already has")
def test_macro__does_not_graduate_while_the_student_lacks_one_of_its_micros(client, bc, student):
    """A micro added to the macro after the enrollment, the student has not synced it yet."""
    first = create_micro(bc, slug="micro-one", days=[{"assignments": ["project-one"]}])
    macro = create_macro(bc, "macro-a", [first], {"micro-one": [{"assignments": [None]}]})
    enroll(bc, student, macro)
    second = create_micro(bc, slug="micro-two", days=[{"assignments": ["project-two"]}])
    macro.cohort.micro_cohorts.add(second.cohort)
    open_micro(client, student, first, macro)

    approve(student, first, "project-one")

    assert edu_status(student, first) == "GRADUATED"
    assert edu_status(student, macro) == "ACTIVE"


# -- micros added later and the sync endpoint --------------------------------------------------------------


def test_sync__adds_missing_micros_with_their_source_macro(client, bc, student):
    first = create_micro(bc, slug="micro-one")
    macro = create_macro(bc, "macro-a", [first])
    enroll(bc, student, macro)
    second = create_micro(bc, slug="micro-two")
    macro.cohort.micro_cohorts.add(second.cohort)
    client.force_authenticate(student)

    response = client.post(reverse_lazy("admissions:me_micro_cohorts_sync", kwargs={"macro_cohort_slug": "macro-a"}))

    assert response.status_code < 400
    assert micro_enrollment(student, second).source_macro_cohort_id == macro.cohort.id


# -- micros that differ per macro (v2 / v3 of the same course) ---------------------------------------------


def test_versioned_micros__each_cohort_keeps_its_own_tasks(client, bc, student):
    old = create_micro(bc, slug="micro-course", version=2, days=[{"assignments": ["project-common"]}])
    new = create_micro(bc, slug="micro-course-new", version=3, days=[{"assignments": ["project-common"]}])
    macro_old = create_macro(bc, "macro-old", [old], {"micro-course": [{"assignments": [None]}]})
    macro_new = create_macro(bc, "macro-new", [new], {"micro-course-new": [{"assignments": [None]}]})
    enroll(bc, student, macro_old)
    open_micro(client, student, old, macro_old)
    approve(student, old, "project-common")

    enroll(bc, student, macro_new)
    open_micro(client, student, new, macro_new)

    assert micro_tasks(student, old)["project-common"].revision_status == "APPROVED"
    assert micro_tasks(student, new)["project-common"].revision_status == "PENDING"
    assert edu_status(student, macro_old) == "GRADUATED"
    assert edu_status(student, macro_new) == "ACTIVE"


# -- learnpack ---------------------------------------------------------------------------------------------


def _complete_learnpack(bc, user, slug):
    from breathecode.assignments.actions import calculate_telemetry_indicator

    bc.database.create(asset={"slug": slug, "graded": True})
    telemetry = AssignmentTelemetry.objects.create(user=user, asset_slug=slug, telemetry={"steps": []})
    scores = {
        "global": {
            "indicators": {"EngagementIndicator": 100, "FrustrationIndicator": 0},
            "metrics": {"total_time_on_platform": 60, "completion_rate": 100},
        }
    }
    with patch("breathecode.assignments.actions.UserIndicatorCalculator") as calculator:
        calculator.return_value.calculate_indicators.return_value = scores
        calculate_telemetry_indicator(telemetry)


def test_learnpack__completion_marks_the_shared_task_done_for_both_macros(client, bc, student):
    micro, general, campus = _shared_micro_world(bc)
    enroll(bc, student, campus)
    enroll(bc, student, general)
    open_micro(client, student, micro, campus)

    _complete_learnpack(bc, student, "exercise-common")

    task = micro_tasks(student, micro)["exercise-common"]
    assert (task.task_status, task.revision_status) == ("DONE", "APPROVED")
    assert Task.objects.filter(user=student, associated_slug="exercise-common").count() == 1
