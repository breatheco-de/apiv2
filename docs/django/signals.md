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

## More about Django Signals

```txt
Source: https://thetldr.tech/how-to-add-custom-signals-dispatch-in-django/
```

Lets take an example app named, application. So we should create a signals.py file in the path application/signals.py with the following content

```py
# application/signals.py

from django import dispatch

some_task_done = dispatch.Signal(providing_args=["task_id"])
```

Here we are creating a custom signal some_task_done which can be imported by any application and called.

Once we have a signal, lets create an use case, i.e. let us call it. For example let us have a tasks.py file which calls the signal. Any other application can also import the signals and then call it.

```py
# application/tasks.py

from application import signals

def do_some_task():
	# did some thing
    signals.some_task_done.send(sender='abc_task_done', task_id=123)

# Here sender can be anything, same are the arguments.
```

So we have seen how to create a signal and how to call it. But we have not seen what happens if we call a signal. This is the most tricky and important part. Whenever we fire a signal, we need some receiver to listen to the signal and perform some action. For this we need to create a receivers.py file (file name can be anything, but try to keep this as a convention for better readability).

```py
# application/receivers.py

from django.dispatch import receiver
from application import signals


@receiver(signals.some_task_done)
def my_task_done(sender, task_id, **kwargs):
    print(sender, task_id)

# prints 'abc_task_done', 123
```

Here the receiver decorator is subscribing to the some_task_done signal and whenever the signal would be dispatched then receiver my_task_done function would be called.

Now comes the most important part. This is something many people miss which makes signals complicated. Make sure to import the receivers in your apps.py this is important since we need to tell django to load the receivers when app is ready, so that it gets linked to the signals framework

```py
# application/apps.py

from django.apps import AppConfig


class ApplicationConfig(AppConfig):
    name = "application"

    def ready(self):
        from application import receivers
```
