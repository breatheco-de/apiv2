import logging, json, os
from typing import Type
from django.dispatch import receiver
from breathecode.admissions.signals import student_edu_status_updated
from breathecode.monitoring.models import StripeEvent
from django.db.models.signals import post_delete, post_save, pre_delete
from breathecode.monitoring import signals as monitoring_signals

from breathecode.provisioning.models import ProvisioningBill

logger = logging.getLogger(__name__)


@receiver(monitoring_signals.stripe_webhook, sender=StripeEvent)
def bill_was_paid(sender: Type[StripeEvent], instance: StripeEvent, **kwargs):
    if instance.type == 'checkout.session.completed':
        try:
            if instance.data['payment_link']:
                ProvisioningBill.objects.filter(stripe_id=instance.data['payment_link']).update(
                    status='PAID', paid_at=instance.created_at)

        except:
            instance.status_texts['provisioning.bill_was_paid'] = 'Invalid context'
            instance.status = 'ERROR'
            instance.save()
            return

        if 'provisioning.bill_was_paid' in instance.status_texts:
            instance.status_texts.pop('provisioning.bill_was_paid')

        instance.status = 'DONE' if len(instance.status_texts) == 0 else 'ERROR'
        instance.save()
