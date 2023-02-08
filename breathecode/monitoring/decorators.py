import logging
from datetime import datetime
from celery import shared_task, Task
from .models import RepositoryWebhook

logger = logging.getLogger(__name__)


def github_webhook_task():

    def decorator(func):

        def inner(*args, **kwargs):
            _self = args[0]
            webhook_id = None
            if isinstance(_self, Task):
                webhook_id = args[1]
            else:
                _self = None
                webhook_id = args[0]

            logger.debug('Starting webhook task')
            status = 'ok'

            webhook = RepositoryWebhook.objects.filter(id=webhook_id).first()
            if webhook is None:
                raise Exception(f'Github Webhook with id {webhook_id} not found')
            webhook.status = 'PENDING'
            webhook.save()

            try:

                if _self is not None:
                    webhook = func(_self, webhook)
                else:
                    webhook = func(webhook)

                webhook.status = 'DONE'
            except Exception as ex:
                webhook.status = 'ERROR'
                webhook.status_text = str(ex)[:255]
                logger.debug(ex)
                status = 'error'

            webhook.run_at = datetime.now()
            webhook.save()

            logger.debug(f'Github Webook processing status: {status}')

        return inner

    return decorator
