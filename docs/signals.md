# Signals

There is a new signals.py and receivers.py logic available to every app. Basically we can create "events" (a.k.a: signals) that are emited when something of interest happens withing any app, then, any other application can start "listening" (a.k.a receiving) to that event and do something about it (similar to the side-effect concept in react.useEffect).

Let's say we want other applications to be notified when a user accepts a new invite, the first we need to do is create a custom signal on the breathecode.authenticate app:

```py
# signals.py

from django import dispatch
invite_accepted = dispatch.Signal(providing_args=["task_id"])
```

Once the signal is registered we need to dispatch it when a user accepts an invite, I decided to add that logice inside the `breathecode.authenticate.models.ProfileAcademy.save()` method, we know for sure that when the ProfileAcademy.status changes from `INVITED` to `ACTIVE` it means that one invite has ben accepted. [Here is the code of the save method](https://github.com/breatheco-de/apiv2/blob/5c6230503eb6104890a1a1c8cc3782172cddeecd/breathecode/authenticate/models.py#L188).

```py
# breathecode.authenticate.models.ProfileAcademy
class ProfileAcademy(models.Model):
    ...
    def save(self, *args, **kwargs):

        if self.__old_status != self.status and self.status == 'ACTIVE':
            invite_accepted.send(instance=self, sender=ProfileAcademy)

        super().save(*args, **kwargs)  # Call the "real" save() method.
```

Now that the triggering of the signal is implemented we can make sure any previous breathecode.marketing.models.FormEntry's`can be connected to the new user that accepted the invite. We can do that by [implementing a receiver](https://github.com/breatheco-de/apiv2/blob/master/breathecode/marketing/receivers.py#L11) for that inside the`receiver.py` inside the marketing app:

```py
# breathecode.marketing.receivers.py

from django.dispatch import receiver
from breathecode.authenticate.signals import invite_accepted
from breathecode.authenticate.models import ProfileAcademy
from .models import FormEntry

@receiver(invite_accepted, sender=ProfileAcademy)
def post_save_profileacademy(sender, instance, **kwargs):
    # if a new ProfileAcademy is created on the authanticate app
    # look for the email on the formentry list and bind it
    entries = FormEntry.objects.filter(email=instance.user.email, user__isnull=True)
    for entry in entries:
        entry.user = instance.user
        entry.save()
```
