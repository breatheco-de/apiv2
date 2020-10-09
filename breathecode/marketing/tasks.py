from celery import shared_task, Task
from .models import FormEntry
from .actions import register_new_lead, save_get_geolocal

class BaseTaskWithRetry(Task):
    autoretry_for = (Exception,)
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5 } 
    retry_backoff = True

@shared_task
def persist_leads():
    entries = FormEntry.objects.filter(storage_status='PENDING')
    for entry in entries:
        form_data = entry.toFormData()
        result = register_new_lead(form_data)
        if result is not None and result != False:
            save_get_geolocal(entry, form_data)
    
    return True

@shared_task(bind=True, base=BaseTaskWithRetry)
def persist_single_lead(self, form_data):
    entry = register_new_lead(form_data)
    if entry is not None and entry != False:
        save_get_geolocal(entry, form_data)
    
    return True