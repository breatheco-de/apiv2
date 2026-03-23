import logging
from typing import Type

from django.dispatch import receiver

from breathecode.authenticate.models import User
from breathecode.monitoring import signals as monitoring_signals
from breathecode.monitoring.models import StripeEvent
from breathecode.payments.models import Consumable, Service
from breathecode.payments.signals import deprovision_service
from breathecode.provisioning.models import ProvisioningBill
from breathecode.utils.decorators.service_deprovisioner import get_service_deprovisioner

logger = logging.getLogger(__name__)


@receiver(monitoring_signals.stripe_webhook, sender=StripeEvent)
def bill_was_paid(sender: Type[StripeEvent], instance: StripeEvent, **kwargs):
    if instance.type == "checkout.session.completed":
        try:
            if instance.data["payment_link"]:
                ProvisioningBill.objects.filter(stripe_id=instance.data["payment_link"]).update(
                    status="PAID", paid_at=instance.created_at
                )

        except Exception:
            instance.status_texts["provisioning.bill_was_paid"] = "Invalid context"
            instance.status = "ERROR"
            instance.save()
            return

        if "provisioning.bill_was_paid" in instance.status_texts:
            instance.status_texts.pop("provisioning.bill_was_paid")

        instance.status = "DONE" if len(instance.status_texts) == 0 else "ERROR"
        instance.save()


@receiver(deprovision_service, sender=Service)
def deprovision_service_receiver(sender: Type[Service], instance: Service, user_id: int, context: dict, **kwargs):
    if not user_id:
        return

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    service_slug = instance.slug

    consumables = Consumable.list(user=user, service=instance)
    if consumables.exists():
        logger.info(f"User {user_id} still has consumables for service {service_slug}, skipping deprovisioning.")
        return

    deprovisioner = get_service_deprovisioner(service_slug)
    if deprovisioner:
        return deprovisioner(user_id=user_id, context=context or {})
    logger.info(f"No deprovisioner found for service {service_slug}")
