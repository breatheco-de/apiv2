import time
from celery import shared_task, Task
from .actions import certificate_screenshot, remove_certificate_screenshot

class BaseTaskWithRetry(Task):
    autoretry_for = (Exception,)
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5 } 
    retry_backoff = True

@shared_task(bind=True, base=BaseTaskWithRetry)
def take_screenshot(self, certificate_id):
    certificate_screenshot(certificate_id)
    return True

@shared_task(bind=True, base=BaseTaskWithRetry)
def remove_screenshot(self, certificate_id):
    remove_certificate_screenshot(certificate_id)
    return True

@shared_task(bind=True, base=BaseTaskWithRetry)
def reset_screenshot(self, certificate_id):

    # just in case, wait for cetificate to save
    remove_certificate_screenshot(certificate_id)
    certificate_screenshot(certificate_id)

    return True