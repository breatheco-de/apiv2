import logging

from celery import Task
from django.utils import timezone

from .models import RepositoryWebhook

logger = logging.getLogger(__name__)


class WebhookTask(Task):
    pending_status = "pending..."

    def initialize(self, webhook_id):

        webhook = RepositoryWebhook.objects.filter(id=webhook_id).first()
        if webhook is None:
            raise Exception(f"Github Webhook with id {webhook_id} not found")
        webhook.status = "PENDING"
        webhook.status_text = self.pending_status
        webhook.save()
        return webhook

    def __call__(self, *args, **kwargs):
        """In celery task this function call the run method, here you can
        set some environment variable before the run of the task"""

        webhook_id = args[0]
        webhook = self.initialize(webhook_id)

        try:
            _webhook = self.run(webhook)

            if isinstance(_webhook, RepositoryWebhook):
                webhook = _webhook
                webhook.status = "DONE"
            else:
                raise Exception("Error while running async webhook task: type != " + str(type(_webhook)))
        except Exception as ex:
            webhook.status = "ERROR"
            webhook.status_text = str(ex)[:255]
            logger.exception(ex)

        webhook.run_at = timezone.now()
        if webhook.status_text == self.pending_status:
            webhook.status_text = "finished"

        webhook.save()

        logger.debug(f"Github Webook processing status: {webhook.status}")
        return webhook.status
