import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from breathecode.authenticate.signals import invite_accepted
from breathecode.authenticate.models import ProfileAcademy
from .models import FormEntry

logger = logging.getLogger(__name__)


@receiver(invite_accepted, sender=ProfileAcademy)
def post_save_profileacademy(sender, instance, **kwargs):
    # if a new ProfileAcademy is created on the authanticate app
    # look for the email on the formentry list and bind it
    logger.debug(
        'Reveiver for invite_accepted triggered, linking the new user to its respective form entries')
    entries = FormEntry.objects.filter(email=instance.user.email, user__isnull=True)
    for entry in entries:
        entry.user = instance.user
        entry.save()
