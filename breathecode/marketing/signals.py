from django.db.models.signals import post_save
from breathecode.authenticate.models import ProfileAcademy
from .models import FormEntry

@receiver(post_save, sender=ProfileAcademy)
def post_save_profileacademy(sender, instance, created, **kwargs):
    # if a new ProfileAcademy is created on the authanticate app
    if created:
        # look for the email on the formentry list and bind it
        entries = FormEntry.objects.filter(email=instance.user.email, user__isnull=True)
        for entry in entries:
            entry.user = instance.user
            entry.save()