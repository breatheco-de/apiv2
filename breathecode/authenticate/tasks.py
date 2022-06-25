import logging, os
from celery import shared_task, Task
from .models import GitpodUser
from .actions import set_gitpod_user_expiration

API_URL = os.getenv('API_URL', '')

logger = logging.getLogger(__name__)


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception, )
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5}
    retry_backoff = True


@shared_task
def async_set_gitpod_user_expiration(gitpoduser_id):
    logger.debug(f'Recalculate gitpoduser expiration for {gitpoduser_id}')
    return set_gitpod_user_expiration(gitpoduser_id) is not None
