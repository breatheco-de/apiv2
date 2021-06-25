import logging
from django.contrib.auth.models import User
from breathecode.marketing.models import FormEntry

logger = logging.getLogger(__name__)

status = {
    "Won": "WON",
    "Lost": "LOST",
    "1": "WON",
    "2": "LOST",
}


def deal_update(self, webhook, payload: dict):
    # prevent circular dependency import between thousand modules previuosly loaded and cached
    from breathecode.marketing.models import FormEntry

    entry = FormEntry.objects.filter(
        ac_deal_id=payload['deal[id]']).order_by('-created_at').first()
    if entry is None and 'deal[contactid]' in payload:
        entry = FormEntry.objects.filter(
            ac_contact_id=payload['deal[contactid]']).order_by(
                '-created_at').first()
    if entry is None and 'deal[contact_email]' in payload:
        entry = FormEntry.objects.filter(email=payload['deal[contact_email]']
                                         ).order_by('-created_at').first()
    if entry is None:
        raise Exception(
            f"Impossible to find formentry for webhook {webhook.id} -> {webhook.webhook_type} "
        )
        logger.debug(payload)

    entry.ac_deal_id = payload['deal[id]']
    entry.ac_contact_id = payload['contact[id]']
    if payload['deal[status]'] in status:
        entry.deal_status = status[payload['deal[status]']]
    entry.save()

    logger.debug(
        f"Form Entry successfuly updated with deal {str(payload['deal[id]'])} information"
    )
    return True
