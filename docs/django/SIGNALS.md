# About Django Signals

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
