#!/usr/bin/env python
"""
Alert when there are Form Entries with status = PENDING
"""
from breathecode.marketing.models import FormEntry
from django.db.models import Q
from breathecode.utils import ScriptNotification

pending_leads = FormEntry.objects.filter(storage_status="PENDING").filter(
    Q(academy__id=academy.id) | Q(location=academy.slug))

if len(pending_leads) > 0:
    raise ScriptNotification(
        f"Warning there are {len(pending_leads)} pending form entries",
        status='MINOR')

print("No pending leads")
