from django.db.models.signals import post_save
from django.dispatch import receiver
from breathecode.authenticate.models import ProfileAcademy
from .models import FormEntry

@receiver(post_save, sender=ProfileAcademy)
def post_save_profileacademy(sender, instance, created, raw, update_fields, **kwargs):
    # if a new ProfileAcademy is created on the authanticate app
    if raw == False and update_fields is not None and "user" in update_fields and update_fields["user"] is not None:
        # look for the email on the formentry list and bind it
        entries = FormEntry.objects.filter(email=instance.user.email, user__isnull=True)
        for entry in entries:
            entry.user = instance.user
            entry.save()