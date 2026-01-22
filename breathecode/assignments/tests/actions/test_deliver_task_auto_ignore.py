import pytest


@pytest.mark.django_db
def test_deliver_task_auto_ignores_project_when_certificate_flag_enabled(database):
    """
    If academy_features.certificate.auto_ignore_projects_on_delivery is True,
    delivering a PROJECT should set revision_status=IGNORED (instead of PENDING).
    """

    from breathecode.assignments.actions import deliver_task
    from breathecode.assignments.models import Task

    model = database.create(user=1, city=1, country=1, academy=1, cohort=1)

    academy = model.academy
    academy.academy_features = academy.academy_features or {}
    academy.academy_features["certificate"] = {"auto_ignore_projects_on_delivery": True}
    academy.save(update_fields=["academy_features"])

    task = Task.objects.create(
        user=model.user,
        cohort=model.cohort,
        associated_slug="my-project",
        title="My Project",
        task_type="PROJECT",
        description="",
    )

    deliver_task("https://github.com/test/repo", live_url="https://example.com", task=task)

    task.refresh_from_db()
    assert task.task_status == "DONE"
    assert task.revision_status == "IGNORED"


