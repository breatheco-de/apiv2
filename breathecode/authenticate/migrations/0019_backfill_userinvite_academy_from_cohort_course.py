from django.db import migrations


def backfill_academy_from_cohort_course(apps, schema_editor):
    """
    For UserInvite rows with academy=None, set academy from cohort.academy or
    course.academy (in that priority order). Rows where cohort and course imply
    different academies are left as-is so that the claim endpoint can raise an
    explicit error when someone tries to claim them.
    """
    UserInvite = apps.get_model("authenticate", "UserInvite")

    null_invites = UserInvite.objects.filter(
        academy__isnull=True
    ).select_related("cohort__academy", "course__academy")

    to_update = []
    for invite in null_invites:
        cohort_academy_id = invite.cohort.academy_id if invite.cohort_id and invite.cohort else None
        course_academy_id = invite.course.academy_id if invite.course_id and invite.course else None

        if cohort_academy_id and course_academy_id and cohort_academy_id != course_academy_id:
            # Conflicting academies — leave null intentionally
            continue

        implied_academy_id = cohort_academy_id or course_academy_id
        if implied_academy_id:
            invite.academy_id = implied_academy_id
            to_update.append(invite)

    if to_update:
        UserInvite.objects.bulk_update(to_update, ["academy_id"])


def reverse_backfill(apps, schema_editor):
    # Not reversible: we can't distinguish which invites were set by this migration.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("authenticate", "0018_userinvite_created_by_admin"),
    ]

    operations = [
        migrations.RunPython(backfill_academy_from_cohort_course, reverse_backfill),
    ]
