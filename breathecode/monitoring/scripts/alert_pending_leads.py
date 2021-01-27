#!/usr/bin/env python
"""
Alert when there are Form Entries with status = PENDING
"""
from breathecode.marketing.models import FormEntry
from django.db.models import Q
pending_leads = FormEntry.objects.filter(storage_status="PENDING").filter(Q(academy__id=academy.id) | Q(location=academy.slug))

if len(pending_leads) > 0:
    result['details'] = f"Warning there are {len(pending_leads)} pending form entries" 
    result['status'] = "MINOR"
else:
    result['status'] = "OPERATIONAL"
    result['details'] = "No pending leads"