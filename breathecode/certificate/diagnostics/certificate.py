"""
Certificate issuance diagnostic: explains why a certificate may not have been generated for a student in a cohort.
"""

from __future__ import annotations

from breathecode.admissions.models import CohortUser, FULLY_PAID, UP_TO_DATE
from breathecode.admissions.utils.academy_features import has_feature_flag
from breathecode.assignments.models import Task
from breathecode.certificate.actions import (
    get_assets_from_syllabus,
    how_many_pending_tasks,
    resolve_specialty_for_cohort,
)
from breathecode.certificate.models import LayoutDesign, UserSpecialty


def _check(slug: str, ok: bool, message: str, severity: str | None = None) -> dict:
    sev = severity or ("ok" if ok else "error")
    return {"slug": slug, "ok": ok, "message": message, "severity": sev}


def build_certificate_diagnostic(cohort_user: CohortUser) -> dict:
    """
    Same logical checks as diagnose_certificate diagnose_cohort_user; returns structured JSON only.
    """
    user = cohort_user.user
    cohort = cohort_user.cohort
    issues: list[str] = []
    warnings: list[str] = []
    checks: list[dict] = []

    checks.append(_check("cohort_user_exists", True, f"CohortUser id={cohort_user.id}", "ok"))

    if cohort.syllabus_version is None:
        issues.append("Cohort has no syllabus_version assigned")
        checks.append(_check("syllabus_version", False, "Cohort has no syllabus_version assigned", "error"))
    else:
        checks.append(
            _check(
                "syllabus_version",
                True,
                f"Cohort has syllabus_version: {cohort.syllabus_version.syllabus.name}",
                "ok",
            )
        )

    specialty = None
    mandatory_projects: list[str] = []
    auto_ignore_enabled = False
    pending_task_samples: list[dict] = []

    if cohort.syllabus_version:
        specialty = resolve_specialty_for_cohort(cohort)
        if not specialty:
            issues.append("Specialty has no Syllabus assigned")
            checks.append(_check("specialty", False, "Specialty has no Syllabus assigned", "error"))
        else:
            checks.append(_check("specialty", True, f"Specialty exists: {specialty.name}", "ok"))

        mandatory_projects = get_assets_from_syllabus(
            cohort.syllabus_version, task_types=["PROJECT"], only_mandatory=True
        )
        has_mandatory = len(mandatory_projects) > 0
        checks.append(
            _check(
                "syllabus_mandatory_projects",
                has_mandatory,
                f"Syllabus has {len(mandatory_projects)} mandatory PROJECT asset(s)",
                "ok" if has_mandatory else "warning",
            )
        )
        if not has_mandatory:
            warnings.append(
                "Syllabus has no mandatory PROJECT entries: SaaS cohorts will not auto-graduate via project "
                "completion, and academy reports typically treat such cohorts as not certificate-eligible."
            )

        academy = cohort.academy
        if academy is not None:
            auto_ignore_enabled = has_feature_flag(
                academy, "certificate.auto_ignore_projects_on_delivery", default=False
            )
            checks.append(
                _check(
                    "certificate_auto_ignore_on_delivery_flag",
                    auto_ignore_enabled,
                    (
                        "Academy feature certificate.auto_ignore_projects_on_delivery is ENABLED "
                        "(delivered PROJECT tasks get revision_status IGNORED)."
                        if auto_ignore_enabled
                        else "Academy feature certificate.auto_ignore_projects_on_delivery is DISABLED "
                        "(delivered PROJECT tasks remain PENDING until teacher APPROVES or IGNORES)."
                    ),
                    "ok" if auto_ignore_enabled else "warning",
                )
            )
            if not auto_ignore_enabled:
                warnings.append(
                    "Without certificate.auto_ignore_projects_on_delivery, delivery sets revision_status=PENDING; "
                    "each mandatory project needs APPROVED or IGNORED for issuance (matches generate_certificate)."
                )
            grading_strategy_msg = (
                "PROJECT grading strategy (academy feature): IGNORE on delivery counts as cleared "
                "(no instructor revision step)."
                if auto_ignore_enabled
                else "PROJECT grading strategy (academy feature): instructor review "
                "(PENDING until APPROVED or IGNORED; only IGNORED/APPROVED count as cleared for certificates)."
            )
            checks.append(
                _check(
                    "project_grading_strategy",
                    True,
                    grading_strategy_msg,
                    "ok",
                )
            )
        else:
            warnings.append("Cohort has no academy set; skipping certificate.auto_ignore_projects_on_delivery check.")

    uspe = UserSpecialty.objects.filter(user=user, cohort=cohort).first()
    if uspe is not None and uspe.status == "PERSISTED" and uspe.preview_url:
        warnings.append(f"User already has a certificate (Status: {uspe.status}, ID: {uspe.id})")
        checks.append(
            _check(
                "existing_certificate",
                True,
                f"UserSpecialty PERSISTED with preview exists (id={uspe.id})",
                "warning",
            )
        )
    elif uspe is not None:
        warnings.append(f"UserSpecialty exists but not fully persisted (Status: {uspe.status}, ID: {uspe.id})")
        checks.append(
            _check(
                "existing_certificate",
                False,
                f"UserSpecialty exists status={uspe.status} (id={uspe.id})",
                "warning",
            )
        )
    else:
        checks.append(_check("existing_certificate", True, "No existing UserSpecialty row", "ok"))

    layout = LayoutDesign.objects.filter(is_default=True, academy=cohort.academy).first()
    if layout is None:
        layout = LayoutDesign.objects.filter(slug="default").first()
    if layout is None:
        issues.append("No layout found (no default layout for academy and no 'default' layout)")
        checks.append(_check("layout", False, "No layout found", "error"))
    else:
        checks.append(_check("layout", True, f"Layout found: {layout.name} (slug: {layout.slug})", "ok"))

    main_teacher = CohortUser.objects.filter(cohort__id=cohort.id, role="TEACHER").first()
    ok_teacher = main_teacher is not None and main_teacher.user is not None
    checks.append(
        _check(
            "main_teacher",
            ok_teacher,
            (
                f"Main teacher: {main_teacher.user.first_name} {main_teacher.user.last_name}"
                if ok_teacher
                else "Cohort does not have a teacher with user"
            ),
            "ok" if ok_teacher else "error",
        )
    )
    if not ok_teacher:
        issues.append("Cohort does not have a main teacher")

    pending_tasks = 0
    if cohort.syllabus_version:
        try:
            pending_tasks = how_many_pending_tasks(
                cohort.syllabus_version,
                user,
                task_types=["PROJECT"],
                only_mandatory=True,
                cohort_id=cohort.id,
            )
            ok_pending = pending_tasks == 0
            checks.append(
                _check(
                    "pending_mandatory_projects",
                    ok_pending,
                    f"Pending mandatory PROJECT tasks: {pending_tasks} (cleared when revision_status is APPROVED or IGNORED)",
                    "ok" if ok_pending else "error",
                )
            )
            if pending_tasks > 0:
                issues.append(f"User has {pending_tasks} pending mandatory PROJECT tasks")
                if mandatory_projects:
                    for task in (
                        Task.objects.filter(
                            user=user, associated_slug__in=mandatory_projects, cohort=cohort
                        )
                        .exclude(revision_status__in=["APPROVED", "IGNORED"])
                        .order_by("id")[:10]
                    ):
                        pending_task_samples.append(
                            {
                                "associated_slug": task.associated_slug,
                                "task_status": task.task_status,
                                "revision_status": task.revision_status,
                            }
                        )
        except Exception as e:
            warnings.append(f"Could not check pending tasks: {str(e)}")
            checks.append(
                _check("pending_mandatory_projects", False, f"Could not check pending tasks: {str(e)}", "warning")
            )

    fin_ok = cohort_user.finantial_status == FULLY_PAID or cohort_user.finantial_status == UP_TO_DATE
    checks.append(
        _check(
            "financial_status",
            fin_ok,
            f"Financial status is '{cohort_user.finantial_status}' (needs FULLY_PAID or UP_TO_DATE)",
            "ok" if fin_ok else "error",
        )
    )
    if not fin_ok:
        issues.append(
            f"Financial status is '{cohort_user.finantial_status}' (must be FULLY_PAID or UP_TO_DATE)"
        )

    edu_ok = cohort_user.educational_status == "GRADUATED"
    checks.append(
        _check(
            "educational_status",
            edu_ok,
            f"Educational status is '{cohort_user.educational_status}' (must be GRADUATED)",
            "ok" if edu_ok else "error",
        )
    )
    if not edu_ok:
        issues.append(f"Educational status is '{cohort_user.educational_status}' (must be GRADUATED)")

    if cohort.never_ends:
        checks.append(_check("cohort_progress", True, "Cohort never_ends is True (skipping current_day)", "ok"))
    else:
        if cohort.syllabus_version:
            expected_days = cohort.syllabus_version.syllabus.duration_in_days
            day_ok = cohort.current_day == expected_days
            checks.append(
                _check(
                    "cohort_current_day",
                    day_ok,
                    f"Cohort current_day is {cohort.current_day} (expected {expected_days})",
                    "ok" if day_ok else "error",
                )
            )
            if not day_ok:
                issues.append(f"Cohort current_day is {cohort.current_day} (expected {expected_days})")

        stage_ok = cohort.stage == "ENDED"
        checks.append(
            _check(
                "cohort_stage",
                stage_ok,
                f"Cohort stage is '{cohort.stage}' (must be ENDED)",
                "ok" if stage_ok else "error",
            )
        )
        if not stage_ok:
            issues.append(f"Cohort stage is '{cohort.stage}' (must be ENDED)")

    summary = (
        "All checks passed; certificate should be generable."
        if not issues
        else f"{len(issues)} issue(s) block certificate generation."
    )

    return {
        "cohort_user_id": cohort_user.id,
        "user_id": user.id,
        "user_email": user.email,
        "cohort_id": cohort.id,
        "cohort_name": cohort.name,
        "academy_id": cohort.academy_id,
        "issues": issues,
        "warnings": warnings,
        "checks": checks,
        "pending_mandatory_tasks_count": pending_tasks,
        "mandatory_project_slugs": list(mandatory_projects),
        "auto_ignore_projects_on_delivery": auto_ignore_enabled,
        "pending_task_samples": pending_task_samples,
        "summary": summary,
    }


def print_certificate_diagnostic(stdout, style: object, cohort_user: CohortUser) -> dict:
    """
    Print the same narrative report as diagnose_certificate.Command._print_diagnostic.

    Args:
        stdout: Management command stdout wrapper (implements .write(str)).
        style: BaseCommand.style (SUCCESS, WARNING, ERROR, ...).

    Returns:
        Structured dict from build_certificate_diagnostic.
    """
    user = cohort_user.user
    cohort = cohort_user.cohort
    result = build_certificate_diagnostic(cohort_user)

    stdout.write(f"\n{'='*80}")
    stdout.write(
        style.SUCCESS(
            f"Usuario: {user.email} (ID: {user.id}) | "
            f"Cohort: {cohort.name} (ID: {cohort.id}) | "
            f"Academia: {cohort.academy.name if cohort.academy else 'N/A'}"
        )
    )
    stdout.write(f"{'='*80}\n")

    for ch in result.get("checks", []):
        sym = "✓" if ch.get("ok") else ("⚠" if ch.get("severity") == "warning" else "❌")
        stdout.write(f"{sym} [{ch.get('slug')}] {ch.get('message')}")

    mp = result.get("mandatory_project_slugs") or []
    if mp:
        if len(mp) <= 10:
            stdout.write(f"\nMandatory PROJECT slugs: {', '.join(mp)}")
        else:
            stdout.write(f"\nMandatory PROJECT slugs (first 10): {', '.join(mp[:10])}...")

    for sample in result.get("pending_task_samples") or []:
        stdout.write(
            f"    • {sample.get('associated_slug')}: task_status={sample.get('task_status')}, "
            f"revision_status={sample.get('revision_status')}"
        )

    stdout.write(f"\n{'─'*80}")
    stdout.write(result.get("summary", ""))
    if result.get("issues"):
        stdout.write(style.ERROR(f"❌ ISSUES FOUND ({len(result['issues'])}):"))
        for i, issue in enumerate(result["issues"], 1):
            stdout.write(style.ERROR(f"  {i}. {issue}"))
    else:
        stdout.write(style.SUCCESS("✓ All checks passed! Certificate should be generable."))

    if result.get("warnings"):
        stdout.write(style.WARNING(f"⚠️  WARNINGS ({len(result['warnings'])}):"))
        for i, warning in enumerate(result["warnings"], 1):
            stdout.write(style.WARNING(f"  {i}. {warning}"))
    stdout.write(f"{'─'*80}\n")

    return result


def list_graduated_without_certificate_cohort_users(academy_id: int | None, limit: int | None):
    """
    CohortUser rows: GRADUATED student, SaaS cohort, no PERSISTED certificate — same as diagnose_certificate --all-graduated.
    """
    query = {
        "educational_status": "GRADUATED",
        "role": "STUDENT",
    }
    cohort_users = CohortUser.objects.filter(**query).exclude(cohort__stage="DELETED")
    if academy_id is not None:
        cohort_users = cohort_users.filter(cohort__academy__id=academy_id)

    graduated_without_cert: list[CohortUser] = []
    for cohort_user in cohort_users.select_related("user", "cohort", "cohort__academy"):
        if not cohort_user.cohort.available_as_saas:
            continue
        has_certificate = UserSpecialty.objects.filter(
            user=cohort_user.user,
            cohort=cohort_user.cohort,
            status="PERSISTED",
        ).exists()
        if not has_certificate:
            graduated_without_cert.append(cohort_user)

    if limit is not None:
        graduated_without_cert = graduated_without_cert[:limit]

    return graduated_without_cert
