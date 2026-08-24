import logging

from django.db import transaction

from breathecode.services.activecampaign.actions.resolve_formentry import (
    bind_deal_to_locked_entry,
    find_formentry_for_deal_payload,
)

logger = logging.getLogger(__name__)


def deal_add(self, webhook, payload: dict, acp_ids):
    from breathecode.marketing.models import FormEntry
    from breathecode.marketing.tasks import async_update_deal_custom_fields

    entry = find_formentry_for_deal_payload(payload, persisted_only=True)
    if entry is None:
        raise Exception(f"Impossible to find formentry for webhook {webhook.id} -> {webhook.webhook_type} ")

    with transaction.atomic():
        locked = FormEntry.objects.select_for_update().get(pk=entry.pk)
        locked = bind_deal_to_locked_entry(locked, payload)
        locked.save()
        entry = locked

    webhook.form_entry = entry
    webhook.save()

    async_update_deal_custom_fields.delay(entry.id)

    logger.debug(f"Form Entry successfuly updated with deal {str(payload['deal[id]'])} information")
    return True
