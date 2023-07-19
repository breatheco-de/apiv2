#!/usr/bin/env python
"""
Reminder for sending surveys to each cohort every 4 weeks
"""
from breathecode.provisioning.models import ProvisioningBill, ProvisioningUserConsumption
from breathecode.utils import ScriptNotification
from breathecode.feedback.models import Survey
from breathecode.admissions.models import Cohort, Academy
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q

bills = ProvisioningBill.objects.filter(academy__id=academy.id, status='ERROR')
activities = ProvisioningUserConsumption.objects.filter(Q(bills__academy__id=academy.id), status='ERROR')

how_many_bills = bills.count()
how_many_activities = activities.count()

if how_many_bills > 0 or how_many_activities > 0:
    raise ScriptNotification(
        f'There are {str(bills.count())} provisioning bills and {str(activities.count())} provisioning '
        'user consumptions with errors',
        status='CRITICAL',
        title=
        f'There are {str(bills.count())} bills and {str(activities.count())} user consumptions with errors',
        slug=f'{how_many_bills}-bills-and-{how_many_activities}-activities-with-errors')

print('All good')
