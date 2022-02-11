## Signals

The official documentation for [django signals can be found here](https://docs.djangoproject.com/en/3.2/topics/signals/).

At BreatheCode, signals are similar concept to "events", we use signals as custom "events" that can notify important things that happen in one app to all the other app's (if they are listening).

For example: When a student drops from a cohort

There is a signal to notify when a `student educational status gets updated`, this is useful because other application may react to it. Here is the [signal being initialized](https://github.com/breatheco-de/apiv2/blob/868486ce4295aeda4dbcac7cb0337c5924d15985/breathecode/admissions/signals.py#L4), here is being triggered/dispatched [when a student gets saved](https://github.com/breatheco-de/apiv2/blob/8b4f937c0dbd6a2edd9717641f2411dd4c759acd/breathecode/admissions/models.py#L305) and this is an example where the [signal is being received on the breathecode.marketing.app](https://github.com/breatheco-de/apiv2/blob/8b4f937c0dbd6a2edd9717641f2411dd4c759acd/breathecode/marketing/receivers.py#L26) to trigger some additional tasks within the system.

## When to use a signal

Inside the breathecode team, we see signals for asynchronous processing of any side effects, we try to focus on them for communication between apps only.

## Declare a new signal

You have many examples that you can find inside the code, each breathecode app has a file `signals.py` that contains all the signals dispatched by that app. If the file does not exist within one of the apps, and you need to create a signal for that app, you can create the file yourself.

If you wanted to create a signal for when a cohort is saved, you should start by initializing it inside `breathecode/admissions/signals.py` like this:

```python
from django.dispatch import Signal

cohort_saved = Signal()
```

## Dispatching a signal

All the initialized signals are available on the same application `signals.py` file, if the signal you want to dispatch is not there, you should probably declare a new one.

After the signal is initialized, it can be dispatched anywhere withing the same app, for example inside a serializer create method like this:

```python
from .signals import cohort_saved

class CohortSerializer(CohortSerializerMixin):

    def create(self, validated_data):
        cohort = Cohort.objects.create(**validated_data, **self.context)
        cohort_saved.send(instance=self, sender=CohortUser)
        return cohort
```

## Receiving a signal

All django applications can subscribe to recieve a signal, even if those signals are coming from another app, but you should always add your receiving code inside the receivers.py of the app that will react to the signal.

The following code will receive the `cohort_saved` signal and print on the screen if its being created or updated.

Note: Its a good idea to always connect receivers to tasks, that way you can asynconosly pospone any processing that you will do after the cohort its created.

```python
from breathecode.admissions.signals import student_edu_status_updated, cohort_saved
from .models import FormEntry, ActiveCampaignAcademy
from .tasks import add_cohort_task_to_student, add_cohort_slug_as_acp_tag

@receiver(cohort_saved, sender=Cohort)
def cohort_post_save(sender, instance, created, *args, **kwargs):
    if created:
        print(f"The cohort {instance.id} was just created")
        # you can call a task from task.py here.
    else:
        print(f"The cohort {instance.id} was just updated")
```
