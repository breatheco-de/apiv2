import logging
from typing import Any, Optional

from capyc.core.i18n import translation
from django.core.cache import cache
from task_manager.core.exceptions import AbortTask, RetryTask
from task_manager.django.decorators import task

from breathecode.authenticate.actions import get_user_settings
from breathecode.notify.models import Notification
from breathecode.utils.decorators import TaskPriority

from .models import File
from .utils import media_settings

logger = logging.getLogger(__name__)
IS_DJANGO_REDIS = hasattr(cache, "fake") is False


@task(bind=False, priority=TaskPriority.STUDENT.value)
def process_file(file_id: int, notification_id: Optional[int] = None, **_: Any):
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

    notification = None
    if notification_id:
        notification = Notification.objects.filter(id=notification_id).first()

    try:
        msg = process(file)
        file.status = File.Status.TRANSFERRED
        file.save()
        if notification:
            notification.send(msg, notification)

    except Exception as e:
        message = f"Error processing file {file_id}: {str(e)}"

        if notification:
            settings = get_user_settings(file.user.id)
            lang = settings.lang
            msg = Notification.error(translation(lang, en="Error processing file", es="Error procesando el archivo"))
            notification.send(msg, notification)

        file.status = File.Status.ERROR
        file.status_message = message
        file.save()
        raise AbortTask(message)
