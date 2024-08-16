import logging
from typing import Any

from django.core.cache import cache
from task_manager.core.exceptions import AbortTask, RetryTask
from task_manager.django.decorators import task

from breathecode.utils.decorators import TaskPriority

from .models import File
from .utils import media_settings

logger = logging.getLogger(__name__)
IS_DJANGO_REDIS = hasattr(cache, "delete_pattern")


@task(bind=False, priority=TaskPriority.STUDENT.value)
def process_file(file_id: int, **_: Any):
    """Renew consumables belongs to a subscription."""

    logger.info(f"Starting process_file for id {file_id}")

    if not (
        file := File.objects.filter(id=file_id, status=File.Status.TRANSFERRING)
        .prefetch_related("user", "academy")
        .first()
    ):
        raise RetryTask(f"File with id {file_id} not found")

    settings = media_settings(file.operation_type)
    if not settings:
        message = f"No settings found for operation type {file.operation_type}"
        file.status = File.Status.ERROR
        file.status_message = message
        file.save()
        raise AbortTask(message)

    process = settings["process"]
    if not callable(process):
        message = f"Invalid process for operation type {file.operation_type}"
        file.status = File.Status.ERROR
        file.status_message = message
        file.save()
        raise AbortTask(message)

    try:
        process(file)
        file.status = File.Status.TRANSFERRED
        file.save()

    except Exception as e:
        message = f"Error processing file {file_id}: {str(e)}"
        file.status = File.Status.ERROR
        file.status_message = message
        file.save()
        raise AbortTask(message)
