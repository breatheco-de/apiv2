#!/usr/bin/env python
"""
Checks if ending date has passed and cohort status is not ended
"""
from breathecode.utils import ScriptNotification
from breathecode.admissions.models import Cohort
from django.utils import timezone

to_fix_cohort_stage = Cohort.objects.filter(ending_date__lt=timezone.now(), academy__id=academy.id)\
    .exclude(stage='ENDED').values_list('name', flat=True)

if len(to_fix_cohort_stage) > 0:
    to_fix_cohort_name = ("\n").join(
        ["- " + cohort_name for cohort_name in to_fix_cohort_stage])

    raise ScriptNotification(
        f"These cohorts ended but their stage is different that ENDED: \n {to_fix_cohort_name}",
        status='MINOR')

else:
    print("Everything up to date")
