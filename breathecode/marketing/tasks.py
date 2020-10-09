from celery import shared_task
from .models import FormEntry
from .actions import register_new_lead


@shared_task
def persist_leads():
    entries = FormEntry.objects.filter(storage_status='PENDING')
    for entry in entries:
        register_new_lead(entry, entry.toFormData())
    
    return True