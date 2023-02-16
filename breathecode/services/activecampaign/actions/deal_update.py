import logging
from django.contrib.auth.models import User
from django.utils import timezone
from breathecode.marketing.models import FormEntry

logger = logging.getLogger(__name__)

status = {
    'Won': 'WON',
    'Lost': 'LOST',
    '1': 'WON',
    '2': 'LOST',
}


def deal_update(self, webhook, payload: dict, acp_ids):
    # prevent circular dependency import between thousand modules previuosly loaded and cached
    from breathecode.marketing.models import FormEntry

    entry = FormEntry.objects.filter(ac_deal_id=payload['deal[id]']).order_by('-created_at').first()
    if entry is None and 'deal[contactid]' in payload:
        entry = FormEntry.objects.filter(
            ac_contact_id=payload['deal[contactid]']).order_by('-created_at').first()
    if entry is None and 'deal[contact_email]' in payload:
        entry = FormEntry.objects.filter(email=payload['deal[contact_email]']).order_by('-created_at').first()
    if entry is None:
        raise Exception(
            f'Impossible to find formentry with deal {payload["deal[id]"]} for webhook {webhook.id} -> '
            f'{webhook.webhook_type} ')

    entry.ac_deal_id = payload['deal[id]']

    if 'contact[id]' in payload:
        entry.ac_contact_id = payload['contact[id]']

    if 'deal[status]' in payload and payload['deal[status]'] in status:

        # check if we just won or lost the deal
        if entry.deal_status is None and status[payload['deal[status]']] == 'WON':
            entry.won_at = timezone.now()
        elif status[payload['deal[status]']] != 'WON':
            entry.won_at = None

        entry.deal_status = status[payload['deal[status]']]
        entry.ac_deal_owner_id = payload['deal[owner]']
        entry.ac_deal_owner_full_name = payload['deal[owner_firstname]'] + ' ' + payload['deal[owner_lastname]']

    if entry.academy is not None:
        logger.debug(f'looking for deal on activecampaign api')
        ac_academy = entry.academy.activecampaignacademy
        fields = self.get_deal_customfields(entry.ac_deal_id)
        if acp_ids['expected_cohort'] in fields:
            entry.ac_expected_cohort = fields[acp_ids['expected_cohort']]
        if acp_ids['expected_cohort_date'] in fields:
            entry.ac_expected_cohort_date = fields[acp_ids['expected_cohort_date']]
    else:
        logger.debug(f'No academy for EntryForm, ignoring deal custom fields')

    entry.save()

    logger.debug(f"Form Entry successfuly updated with deal {str(payload['deal[id]'])} information")
    return True
