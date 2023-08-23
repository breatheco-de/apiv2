import logging
from django.dispatch import receiver
import breathecode.certificate.tasks as tasks
from .models import UserSpecialty
from .signals import user_specialty_saved
from breathecode.admissions.signals import student_edu_status_updated
from breathecode.admissions.models import CohortUser

logger = logging.getLogger(__name__)


@receiver(user_specialty_saved, sender=UserSpecialty)
def post_save_user_specialty(sender, instance: UserSpecialty, **kwargs):
    if instance._hash_was_updated and instance.status == 'PERSISTED' and instance.preview_url:
        tasks.reset_screenshot.delay(instance.id)

    elif instance._hash_was_updated and instance.status == 'PERSISTED' and not instance.preview_url:
        tasks.take_screenshot.delay(instance.id)


@receiver(student_edu_status_updated, sender=CohortUser)
def generate_certificate(sender, instance: CohortUser, **kwargs):
    print(instance)
    if instance.educational_status == 'GRADUATED':
        tasks.generate_one_certificate(instance.cohort.id, instance.user.id, None)
