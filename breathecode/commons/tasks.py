import importlib
import logging

from task_manager.core.exceptions import AbortTask, RetryTask
from task_manager.django.decorators import task

from breathecode.commons import actions
from breathecode.utils import CACHE_DESCRIPTORS
from breathecode.utils.decorators import TaskPriority

logger = logging.getLogger(__name__)

MODULES = {}


@task(bind=True, priority=TaskPriority.CACHE.value)
def clean_task(self, key: str, task_manager_id: int):
    # make sure all the modules are loaded
    from breathecode.admissions import caches as _  # noqa: F811, F401
    from breathecode.assignments import caches as _  # noqa: F811, F401
    from breathecode.events import caches as _  # noqa: F811, F401
    from breathecode.feedback import caches as _  # noqa: F811, F401
    from breathecode.marketing import caches as _  # noqa: F811, F401
    from breathecode.mentorship import caches as _  # noqa: F811, F401
    from breathecode.payments import caches as _  # noqa: F811, F401
    from breathecode.registry import caches as _  # noqa: F811, F401

    task_cls = self.task_manager.__class__
    task_cls.objects.filter(
        status="SCHEDULED",
        task_module=self.task_manager.task_module,
        task_name=self.task_manager.task_name,
        arguments__args__exact=[key],
        arguments__args__len=1,
    ).exclude(id=task_manager_id).delete()

    unpack = key.split(".")
    model = unpack[-1]
    module = ".".join(unpack[:-1])

    if module not in MODULES:
        MODULES[module] = importlib.import_module(module)

    module = MODULES[module]
    model_cls = getattr(module, model)

    if model_cls not in CACHE_DESCRIPTORS:
        raise AbortTask(f"Cache not implemented for {model_cls.__name__}, skipping", log=actions.is_output_enable())

    cache = CACHE_DESCRIPTORS[model_cls]

    try:
        cache.clear()
        if actions.is_output_enable():
            logger.debug(f"Cache cleaned for {key}")

    except Exception:
        raise RetryTask(f"Could not clean the cache {key}", log=actions.is_output_enable())
