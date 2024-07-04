import logging

from django.utils import timezone

status = {
    "Won": "WON",
    "Lost": "LOST",
    "0": None,
    "1": "WON",
    "2": "LOST",
}

logger = logging.getLogger(__name__)


def deal_add(self, webhook, payload: dict, acp_ids):
    # prevent circular dependency import between thousand modules previuosly loaded and cached
    from breathecode.marketing.models import FormEntry
    from breathecode.marketing.tasks import async_update_deal_custom_fields

    entry = (
        FormEntry.objects.filter(ac_deal_id=payload["deal[id]"], storage_status="PERSISTED")
        .order_by("-created_at")
        .first()
    )
    if entry is None and "deal[contactid]" in payload:
        entry = (
            FormEntry.objects.filter(
                ac_contact_id=payload["deal[contactid]"], ac_deal_id__isnull=True, storage_status="PERSISTED"
            )
            .order_by("-created_at")
            .first()
        )
    if entry is None and "deal[contact_email]" in payload:
        entry = (
            FormEntry.objects.filter(
                email=payload["deal[contact_email]"], ac_deal_id__isnull=True, storage_status="PERSISTED"
            )
            .order_by("-created_at")
            .first()
        )
    if entry is None:
        raise Exception(f"Impossible to find formentry for webhook {webhook.id} -> {webhook.webhook_type} ")
        logger.debug(payload)

    entry.ac_deal_id = payload["deal[id]"]
    entry.ac_contact_id = payload["deal[contactid]"]
    if payload["deal[status]"] in status:

        # check if we just won or lost the deal
        if entry.deal_status is None and status[payload["deal[status]"]] == "WON":
            entry.won_at = timezone.now()
        elif status[payload["deal[status]"]] != "WON":
            entry.won_at = None

        entry.deal_status = status[payload["deal[status]"]]
        entry.ac_deal_owner_id = payload["deal[owner]"]
        entry.ac_deal_owner_full_name = payload["deal[owner_firstname]"] + " " + payload["deal[owner_lastname]"]

        entry.ac_deal_amount = float(payload["deal[value_raw]"])
        entry.ac_deal_currency_code = payload["deal[currency]"]

    entry.save()

    # update entry on the webhook
    webhook.form_entry = entry
    webhook.save()

    async_update_deal_custom_fields.delay(entry.id)

    logger.debug(f"Form Entry successfuly updated with deal {str(payload['deal[id]'])} information")
    return True
