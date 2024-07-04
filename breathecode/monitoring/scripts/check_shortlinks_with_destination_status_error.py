#!/usr/bin/env python
"""
Alert when there are Marketing ShortLinks with destination_status=error or not_found:

The email notification must include the list of shortlinks that are failing, each of them with the destination_status, destination_status_text and
when was the last time it was clicked (Ex.g: 2 days ago) and the link to click it that opens the destination.
"""

# flake8: noqa: F821

import datetime
from breathecode.marketing.models import ShortLink
from breathecode.utils import ScriptNotification
from django.db.models import Q

# start your code here
# Filtered list of shortlink objects with destination status error or not found
destination_status_error_or_not_found = ShortLink.objects.filter(
    Q(destination_status="ERROR") | Q(destination_status="NOT_FOUND")
)

destination_status_error_or_not_found_list = [
    "- URL: "
    + item.destination
    + " Status: "
    + item.destination_status
    + " Last clicked: "
    + f'{item.lastclick_at.strftime("%m/%d/%Y, %H:%M:%S") if item.lastclick_at != None else "never"}'
    for item in destination_status_error_or_not_found
]

# Joining the list together for a display format
destination_status_error_or_not_found_list_display = ("\n").join(destination_status_error_or_not_found_list)

if len(destination_status_error_or_not_found_list_display) > 0:
    raise ScriptNotification(
        f"These shortlinks: {destination_status_error_or_not_found_list_display} are not working properly.",
        slug="short-link-bad-destination-status",
    )

print("All shortlinks working properly")
