"""
Certificate issuance diagnostic: explains why a certificate may not have been generated for a student in a cohort.
"""

from __future__ import annotations

from breathecode.admissions.models import CohortUser, FULLY_PAID, UP_TO_DATE
from breathecode.certificate.actions import how_many_pending_tasks, resolve_specialty_for_cohort
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
    if cohort.syllabus_version:
        specialty = resolve_specialty_for_cohort(cohort)
        if not specialty:
            issues.append("Specialty has no Syllabus assigned")
            checks.append(_check("specialty", False, "Specialty has no Syllabus assigned", "error"))
        else:
            checks.append(_check("specialty", True, f"Specialty exists: {specialty.name}", "ok"))

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
            ok_pending = not pending_tasks or pending_tasks == 0
            checks.append(
                _check(
                    "pending_mandatory_projects",
                    ok_pending,
                    f"Pending mandatory PROJECT tasks: {pending_tasks}",
                    "ok" if ok_pending else "error",
                )
            )
            if pending_tasks and pending_tasks > 0:
                issues.append(f"User has {pending_tasks} pending mandatory PROJECT tasks")
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
        "summary": summary,
    }


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
