import logging
from django.dispatch import receiver
from breathecode.authenticate.signals import academy_invite_accepted
from breathecode.events.signals import event_saved
from breathecode.authenticate.models import ProfileAcademy
from breathecode.admissions.models import CohortUser, Cohort, Academy
from breathecode.events.models import Event
from breathecode.admissions.signals import student_edu_status_updated, cohort_saved, academy_saved
from .models import FormEntry, ActiveCampaignAcademy
import breathecode.marketing.tasks as tasks
from .models import Downloadable, AcademyAlias
from .signals import downloadable_saved
from .tasks import add_downloadable_slug_as_acp_tag

logger = logging.getLogger(__name__)


@receiver(academy_invite_accepted, sender=ProfileAcademy)
def post_save_profileacademy(sender, instance, **kwargs):
    # if a new ProfileAcademy is created on the authanticate app
    # look for the email on the formentry list and bind it
    logger.debug("Receiver for academy_invite_accepted triggered, linking the new user to its respective form entries")
    entries = FormEntry.objects.filter(email=instance.user.email, user__isnull=True)
    for entry in entries:
        entry.user = instance.user
        entry.save()


@receiver(student_edu_status_updated, sender=CohortUser)
def student_edustatus_updated(sender, instance, *args, **kwargs):
    if instance.educational_status == "ACTIVE":
        logger.warning(f"Student is now active in cohort `{instance.cohort.slug}`, processing task")
        tasks.add_cohort_task_to_student.delay(instance.user.id, instance.cohort.id, instance.cohort.academy.id)


@receiver(cohort_saved, sender=Cohort)
def cohort_post_save(sender, instance, created, *args, **kwargs):
    if created:
        ac_academy = ActiveCampaignAcademy.objects.filter(academy__id=instance.academy.id).first()
        if ac_academy is not None:
            tasks.add_cohort_slug_as_acp_tag.delay(instance.id, instance.academy.id)


@receiver(academy_saved, sender=Academy)
def academy_post_save(sender, instance, created, *args, **kwargs):
    if created:
        alias = AcademyAlias.objects.filter(slug=instance.slug).first()
        if alias is None:
            slug = instance.active_campaign_slug
            if slug is None:
                slug = instance.slug

            alias = AcademyAlias(slug=instance.slug, active_campaign_slug=slug, academy=instance)
            alias.save()


@receiver(event_saved, sender=Event)
def event_post_saved(sender, instance: Event, created: bool, *args, **kwargs):
    if created and instance.slug and instance.academy:
        tasks.add_event_slug_as_acp_tag.delay(instance.id, instance.academy.id)


@receiver(downloadable_saved, sender=Downloadable)
def downloadable_post_save(sender, instance, created, *args, **kwargs):
    if created:
        ac_academy = ActiveCampaignAcademy.objects.filter(academy__id=instance.academy.id).first()
        if ac_academy is not None:
            add_downloadable_slug_as_acp_tag.delay(instance.id, instance.academy.id)
