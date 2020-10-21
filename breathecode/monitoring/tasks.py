from celery import shared_task, Task
from .actions import run_app_diagnostig
from .models import Application
from breathecode.notify.actions import send_email_message
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

class BaseTaskWithRetry(Task):
    autoretry_for = (Exception,)
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5 } 
    retry_backoff = True

@shared_task(bind=True, base=BaseTaskWithRetry)
def monitor_app(self,app_id):
    app = Application.objects.get(id=app_id)
    result = run_app_diagnostig(app)
    if result["status"] != "OPERATIONAL":
        send_email_message("diagnostig", app.notify_email, {
            "subject": f"Errors have been found on {app.title} diagnostig",
            "details": result["text"]
        })