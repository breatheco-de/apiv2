"""
Graduation diagnostic: explains why automatic SaaS graduation may not have run for a CohortUser.
"""

from __future__ import annotations

from breathecode.admissions.models import CohortUser
from breathecode.admissions.services.completion import evaluate_cohort_user_completion
from breathecode.admissions.utils.academy_features import has_feature_flag
from breathecode.assignments.models import Task
from breathecode.certificate.actions import get_assets_from_syllabus


def _check(slug: str, ok: bool, message: str, severity: str | None = None) -> dict:
    sev = severity or ("ok" if ok else "error")
    return {"slug": slug, "ok": ok, "message": message, "severity": sev}


def build_graduation_diagnostic(cohort_user: CohortUser) -> dict:
    """
    Run the same logical checks as diagnose_graduation management command; return structured JSON only.
    """
    user = cohort_user.user
    cohort = cohort_user.cohort
    issues: list[str] = []
    warnings: list[str] = []
    checks: list[dict] = []

    checks.append(
        _check(
            "educational_status",
            True,
            f"Current educational_status is {cohort_user.educational_status}",
            "ok",
        )
    )

    completion = evaluate_cohort_user_completion(cohort_user)

    if cohort_user.educational_status == "GRADUATED":
        return {
            "cohort_user_id": cohort_user.id,
            "user_id": user.id,
            "user_email": user.email,
            "cohort_id": cohort.id,
            "cohort_name": cohort.name,
            "already_graduated": True,
            "issues": [],
            "warnings": [],
            "checks": checks,
            "mandatory_projects": [],
            "pending_mandatory_tasks_count": 0,
            "pending_task_samples": [],
            "auto_ignore_enabled": False,
            "project_revision_summary": None,
            "completion": completion,
            "summary": "User is already GRADUATED.",
        }

    ok_saas = cohort.available_as_saas
    checks.append(
        _check(
            "cohort_available_as_saas",
            ok_saas,
            f"Cohort available_as_saas is {cohort.available_as_saas} (must be True for automatic graduation)",
            "ok" if ok_saas else "error",
        )
    )
    if not ok_saas:
        issues.append("Cohort is not available_as_saas (must be True for automatic graduation)")

    if not cohort.syllabus_version:
        issues.append("Cohort has no syllabus_version")
        checks.append(
            _check("syllabus_version", False, "Cohort has no syllabus_version", "error"),
        )
        return {
            "cohort_user_id": cohort_user.id,
            "user_id": user.id,
            "user_email": user.email,
            "cohort_id": cohort.id,
            "cohort_name": cohort.name,
            "already_graduated": False,
            "issues": issues,
            "warnings": warnings,
            "checks": checks,
            "mandatory_projects": [],
            "pending_mandatory_tasks_count": 0,
            "pending_task_samples": [],
            "auto_ignore_enabled": False,
            "project_revision_summary": None,
            "summary": "Cannot continue diagnostic without syllabus_version.",
        }

    checks.append(
        _check(
            "syllabus_version",
            True,
            f"Cohort has syllabus_version: {cohort.syllabus_version.syllabus.name}",
            "ok",
        )
    )

    mandatory_projects = get_assets_from_syllabus(
        cohort.syllabus_version, task_types=["PROJECT"], only_mandatory=True
    )
    checks.append(
        _check(
            "completion_strategy",
            completion["strategy"]["type"] != "NO_COMPLETION_STRATEGY",
            f"Completion strategy is {completion['strategy']['type']} from {completion['strategy']['source']}",
            "ok" if completion["strategy"]["type"] != "NO_COMPLETION_STRATEGY" else "error",
        )
    )
    if completion["strategy"]["type"] == "NO_COMPLETION_STRATEGY":
        issues.append("Syllabus has no completion strategy and no mandatory projects for legacy graduation")

    academy = cohort.academy
    auto_ignore_enabled = has_feature_flag(academy, "certificate.auto_ignore_projects_on_delivery", default=False)
    checks.append(
        _check(
            "auto_ignore_feature_flag",
            auto_ignore_enabled,
            f"Auto-ignore on delivery is {'ENABLED' if auto_ignore_enabled else 'DISABLED'} for academy {academy.id}",
            "ok" if auto_ignore_enabled else "warning",
        )
    )
    if not auto_ignore_enabled:
        warnings.append(
            "Auto-ignore feature flag is disabled; projects will not be auto-ignored when delivered."
        )

    pending_tasks = completion["pending_required_count"]
    ok_pending = pending_tasks == 0
    checks.append(
        _check(
            "pending_completion_requirements",
            ok_pending,
            f"Pending required assets: {pending_tasks}",
            "ok" if ok_pending else "error",
        )
    )
    if pending_tasks > 0:
        issues.append(f"User has {pending_tasks} pending required asset(s)")

    pending_task_samples: list[dict] = []
    pending_slugs = []
    for slugs in completion["pending_required_slugs"].values():
        pending_slugs.extend(slugs)
    if pending_slugs:
        user_tasks_pending = Task.objects.filter(user=user, associated_slug__in=pending_slugs, cohort=cohort)
        task_samples_by_slug = {task.associated_slug: task for task in user_tasks_pending[:10]}
        for slug in pending_slugs[:10]:
            task = task_samples_by_slug.get(slug)
            pending_task_samples.append(
                {
                    "associated_slug": slug,
                    "task_status": task.task_status if task else None,
                    "revision_status": task.revision_status if task else None,
                }
            )

    fin_ok = cohort_user.finantial_status != "LATE"
    checks.append(
        _check(
            "financial_status",
            fin_ok,
            f"Financial status is {cohort_user.finantial_status}"
            + (" (LATE blocks manual graduation via API)" if cohort_user.finantial_status == "LATE" else ""),
            "ok" if fin_ok else "error",
        )
    )
    if cohort_user.finantial_status == "LATE":
        issues.append("Financial status is LATE (blocks manual graduation via API)")

    user_tasks_all = Task.objects.filter(user=user, cohort=cohort, task_type="PROJECT")
    tasks_with_revision = user_tasks_all.exclude(revision_status__in=["", None])

    project_revision_summary = None
    all_tasks_approved = False

    if tasks_with_revision.count() == 0:
        warnings.append(
            "No PROJECT tasks with revision_status set (receiver triggers on revision_status_updated)."
        )
        checks.append(
            _check(
                "project_revision_signals",
                False,
                "No PROJECT tasks with revision_status found",
                "warning",
            )
        )
    else:
        approved_tasks = tasks_with_revision.filter(revision_status="APPROVED")
        ignored_tasks = tasks_with_revision.filter(revision_status="IGNORED")
        pending_tasks_list = tasks_with_revision.exclude(revision_status__in=["APPROVED", "IGNORED"])
        project_revision_summary = {
            "with_revision_count": tasks_with_revision.count(),
            "approved_count": approved_tasks.count(),
            "ignored_count": ignored_tasks.count(),
            "pending_or_other_count": pending_tasks_list.count(),
        }
        checks.append(
            _check(
                "project_revision_signals",
                True,
                f"PROJECT tasks with revision_status: approved={approved_tasks.count()}, "
                f"ignored={ignored_tasks.count()}, pending/other={pending_tasks_list.count()}",
                "ok",
            )
        )

        mandatory_tasks = user_tasks_all.filter(associated_slug__in=mandatory_projects)
        all_tasks_approved = (
            mandatory_tasks.exclude(revision_status__in=["APPROVED", "IGNORED"]).count() == 0
            and mandatory_tasks.filter(revision_status="APPROVED").count() > 0
        )

        if pending_tasks == 0 and approved_tasks.count() > 0:
            warnings.append(
                "Receiver mark_saas_student_as_graduated only runs when revision_status is updated (event-driven). "
                "If tasks were already approved before the receiver ran, the user may not auto-graduate."
            )

    conditions_met_but_not_graduated = len(issues) == 0 and completion["is_complete"] and cohort_user.educational_status != "GRADUATED"

    summary_parts = []
    if conditions_met_but_not_graduated:
        summary_parts.append(
            "All automated checks pass and completion requirements are met, but user is not GRADUATED — "
            "likely the graduation receiver did not run on the last relevant task update."
        )
    elif len(issues) == 0:
        summary_parts.append(
            "All blocking checks passed; graduation should occur when a required asset update makes completion reach the strategy threshold."
        )
    else:
        summary_parts.append(f"{len(issues)} issue(s) prevent graduation until resolved.")

    return {
        "cohort_user_id": cohort_user.id,
        "user_id": user.id,
        "user_email": user.email,
        "cohort_id": cohort.id,
        "cohort_name": cohort.name,
        "already_graduated": False,
        "issues": issues,
        "warnings": warnings,
        "checks": checks,
        "mandatory_projects": list(mandatory_projects),
        "pending_mandatory_tasks_count": pending_tasks,
        "pending_task_samples": pending_task_samples,
        "auto_ignore_enabled": auto_ignore_enabled,
        "project_revision_summary": project_revision_summary,
        "completion": completion,
        "all_mandatory_tasks_approved_pattern": all_tasks_approved,
        "conditions_met_but_not_graduated": conditions_met_but_not_graduated,
        "possible_reasons_if_stuck": (
            [
                "Tasks were approved before the receiver was deployed",
                "The receiver did not run when the last task was approved",
                "An error occurred when the receiver ran",
                "The revision_status_updated signal was not sent",
            ]
            if conditions_met_but_not_graduated
            else []
        ),
        "summary": " ".join(summary_parts),
    }
