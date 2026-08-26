import logging

from django.db import transaction

from breathecode.marketing.models import AcademyAlias
from breathecode.services.activecampaign.actions.resolve_formentry import (
    bind_deal_to_locked_entry,
    find_formentry_for_deal_payload,
)

logger = logging.getLogger(__name__)


def deal_update(ac_cls, webhook, payload: dict, acp_ids):
    from breathecode.marketing.models import FormEntry

    entry = find_formentry_for_deal_payload(payload, persisted_only=True)
    if entry is None:
        raise Exception(
            f'Impossible to find formentry with deal {payload["deal[id]"]} for webhook {webhook.id} -> '
            f"{webhook.webhook_type} "
        )

    logger.debug("looking for deal on activecampaign api")
    deal_custom_fields = ac_cls.get_deal_customfields(payload["deal[id]"])

    with transaction.atomic():
        locked = FormEntry.objects.select_for_update().get(pk=entry.pk)
        locked = bind_deal_to_locked_entry(locked, payload)

        # WARNING: Do not update the utm's back to breathecode, we want to keep the original trace
        locked = update_expected_cohort(ac_cls, locked, acp_ids, deal_custom_fields)
        locked = update_location(ac_cls, locked, acp_ids, deal_custom_fields)
        locked = update_course(ac_cls, locked, acp_ids, deal_custom_fields)

        locked.custom_fields = deal_custom_fields
        locked.save()
        entry = locked

    webhook.form_entry = entry
    webhook.save()

    logger.debug(f"Form Entry successfuly updated with deal {str(payload['deal[id]'])} information")
    return True


def update_course(ac_cls, entry, acp_ids, deal_custom_fields):
    deal_ids = acp_ids["deal"]

    if deal_ids["utm_course"] in deal_custom_fields:
        new_course = deal_custom_fields[deal_ids["utm_course"]]
        if new_course is not None and new_course != "":
            entry.ac_deal_course = new_course

    return entry


def update_location(ac_cls, entry, acp_ids, deal_custom_fields):
    deal_ids = acp_ids["deal"]

    if deal_ids["utm_location"] in deal_custom_fields:
        new_location = deal_custom_fields[deal_ids["utm_location"]]
        if new_location is not None and entry.location != new_location and new_location != "":
            entry.ac_deal_location = new_location

            new_alias = AcademyAlias.objects.filter(slug=new_location).first()
            if new_alias and new_alias.academy is not None:
                entry.academy = new_alias.academy

    return entry


def update_expected_cohort(ac_cls, entry, acp_ids, deal_custom_fields):
    deal_ids = acp_ids["deal"]

    if entry.academy is not None:
        if deal_ids["expected_cohort"] in deal_custom_fields:
            entry.ac_expected_cohort = deal_custom_fields[deal_ids["expected_cohort"]]
        if deal_ids["expected_cohort_date"] in deal_custom_fields:
            entry.ac_expected_cohort_date = deal_custom_fields[deal_ids["expected_cohort_date"]]
    else:
        logger.debug("No academy for EntryForm, ignoring deal custom fields")
    return entry
