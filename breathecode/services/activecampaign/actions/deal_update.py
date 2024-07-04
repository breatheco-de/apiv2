import logging
from django.utils import timezone
from breathecode.marketing.models import AcademyAlias

logger = logging.getLogger(__name__)

status = {
    "Won": "WON",
    "Lost": "LOST",
    "0": None,
    "1": "WON",
    "2": "LOST",
}


# FIXME: it's unused
def deal_update(ac_cls, webhook, payload: dict, acp_ids):
    # prevent circular dependency import between thousand modules previuosly loaded and cached
    from breathecode.marketing.models import FormEntry

    entry = (
        FormEntry.objects.filter(ac_deal_id=payload["deal[id]"], storage_status="PERSISTED")
        .order_by("-created_at")
        .first()
    )
    if entry is None and "deal[contactid]" in payload:
        entry = (
            FormEntry.objects.filter(ac_contact_id=payload["deal[contactid]"], storage_status="PERSISTED")
            .order_by("-created_at")
            .first()
        )
    if entry is None and "deal[contact_email]" in payload:
        entry = (
            FormEntry.objects.filter(email=payload["deal[contact_email]"], storage_status="PERSISTED")
            .order_by("-created_at")
            .first()
        )
    if entry is None:
        raise Exception(
            f'Impossible to find formentry with deal {payload["deal[id]"]} for webhook {webhook.id} -> '
            f"{webhook.webhook_type} "
        )

    entry.ac_deal_id = payload["deal[id]"]

    if "contact[id]" in payload:
        entry.ac_contact_id = payload["contact[id]"]

    if "deal[status]" in payload and payload["deal[status]"] in status:

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

    # lets get the custom fields and use them to update some local fields
    logger.debug("looking for deal on activecampaign api")
    deal_custom_fields = ac_cls.get_deal_customfields(entry.ac_deal_id)

    # WARNING: Do not update the utm's back to breathecode, we want to keep the original trace
    entry = update_expected_cohort(ac_cls, entry, acp_ids, deal_custom_fields)
    entry = update_location(ac_cls, entry, acp_ids, deal_custom_fields)
    entry = update_course(ac_cls, entry, acp_ids, deal_custom_fields)

    entry.custom_fields = deal_custom_fields
    entry.save()

    # update entry on the webhook
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
