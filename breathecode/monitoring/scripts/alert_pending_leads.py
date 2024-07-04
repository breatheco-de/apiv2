#!/usr/bin/env python
"""
Alert when there are Form Entries with status = PENDING
"""

# flake8: noqa: F821

from breathecode.marketing.models import FormEntry
from django.db.models import Q
from breathecode.utils import ScriptNotification
from breathecode.utils.datetime_integer import from_now

pending_leads = FormEntry.objects.filter(storage_status="PENDING").filter(
    Q(academy__id=academy.id) | Q(location=academy.slug)
)

leads_html = ""
for l in pending_leads:
    # beware!! from_now cannot be used inside a map or join function, you have to do a traditional for loop
    leads_html += f"- {l.first_name} {l.last_name} {l.email} added {from_now(l.created_at)} ago. \n"

if len(pending_leads) > 0:
    raise ScriptNotification(
        f"The following {len(pending_leads)} leads could not be added to CRM and need to be reviewed: \n\n"
        + leads_html,
        status="CRITICAL",
        title=f"{str(len(pending_leads))} leads from {academy.name} could not be added to CRM",
        slug="pending-academy-leads",
        btn_url=ADMIN_URL + "/growth/leads?location=" + academy.slug + "&limit=10&offset=0&storage_status=PENDING",
    )

print(f"No pending leads for {academy.name}")
