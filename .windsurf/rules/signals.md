---
trigger: glob
description:
globs: **/signals.py,**/receivers.py
---

# Django Signals

- Django config file [settings.py](mdc:breathecode/settings.py)
- Celery config file [celery.py](mdc:breathecode/celery.py)
- All declared Signals in this project must use Capy Core Emisors https://breatheco-de.github.io/celery-task-manager-django-plugin/getting-started/emisors/
- If you are thinking about create a signal to then call a Celery Task [celery.mdc](mdc:.cursor/rules/celery.mdc) you could use instead `.delay` and `.adelay` from https://breatheco-de.github.io/celery-task-manager-django-plugin/getting-started/emisors/
- You MUST avoid overload a single operation with signals, use Celery Task and Capy Core Signal `.delay` and `.adelay` instead
- Avoid async code within Celery Tasks and Capy Core Signals
- You must to load your `receivers.py` files within an `apps.py` file
