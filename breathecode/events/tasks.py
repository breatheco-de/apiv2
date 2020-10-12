from celery import shared_task, Task
from .models import Organization
from .actions import sync_org_events

class BaseTaskWithRetry(Task):
    autoretry_for = (Exception,)
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5 } 
    retry_backoff = True

@shared_task(bind=True, base=BaseTaskWithRetry)
def persist_organization_events(self,args):
    org = Organization.objects.get(id=args['org_id'])
    result = sync_org_events(org)

    return True