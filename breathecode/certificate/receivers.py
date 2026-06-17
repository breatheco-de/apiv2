import logging

from django.core.exceptions import ValidationError
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

import breathecode.certificate.tasks as tasks
from breathecode.admissions.models import CohortUser, Syllabus
from breathecode.admissions.signals import student_edu_status_updated

from .actions import get_syllabus_specialty_bucket_conflict
from .models import Specialty, UserSpecialty
from .signals import user_specialty_saved

logger = logging.getLogger(__name__)


@receiver(user_specialty_saved, sender=UserSpecialty)
def post_save_user_specialty(sender, instance: UserSpecialty, **kwargs):
    if instance._hash_was_updated and instance.status == "PERSISTED" and instance.preview_url:
        tasks.reset_screenshot.delay(instance.id)

    elif instance._hash_was_updated and instance.status == "PERSISTED" and not instance.preview_url:
        tasks.take_screenshot.delay(instance.id)


@receiver(student_edu_status_updated, sender=CohortUser)
def generate_certificate(sender, instance: CohortUser, **kwargs):
    cohort = instance.cohort
    logger.info(
        "[GENERATE_CERTIFICATE] signal student_edu_status_updated user_id=%s cohort_id=%s "
        "educational_status=%s available_as_saas=%s",
        instance.user_id,
        cohort.id if cohort else None,
        instance.educational_status,
        cohort.available_as_saas if cohort else None,
    )

    if not cohort:
        logger.warning(
            "[GENERATE_CERTIFICATE] signal skipped reason=no-cohort user_id=%s",
            instance.user_id,
        )
        return

    if not cohort.available_as_saas:
        logger.info(
            "[GENERATE_CERTIFICATE] signal skipped reason=not-saas user_id=%s cohort_id=%s",
            instance.user_id,
            cohort.id,
        )
        return

    if instance.educational_status != "GRADUATED":
        logger.info(
            "[GENERATE_CERTIFICATE] signal skipped reason=not-graduated user_id=%s cohort_id=%s status=%s",
            instance.user_id,
            cohort.id,
            instance.educational_status,
        )
        return

    tasks.async_generate_certificate.delay(instance.cohort.id, instance.user.id)
    logger.info(
        "[GENERATE_CERTIFICATE] async task enqueued user_id=%s cohort_id=%s task=async_generate_certificate",
        instance.user_id,
        cohort.id,
    )


@receiver(m2m_changed, sender=Specialty.syllabuses.through)
def enforce_specialty_syllabus_bucket_uniqueness(sender, instance, action, reverse, model, pk_set, **kwargs):
    """One specialty per syllabus per academy bucket (or one global); blocks admin/M2M bypass of API rules."""
    if action != "pre_add" or reverse or not pk_set:
        return
    if not instance.pk:
        return
    for syllabus_id in pk_set:
        syllabus = Syllabus.objects.filter(pk=syllabus_id).first()
        if not syllabus:
            continue
        conflict = get_syllabus_specialty_bucket_conflict(instance, syllabus)
        if conflict:
            raise ValidationError(
                f"Another specialty (slug={conflict.slug}) already links this syllabus in the same academy scope."
            )
