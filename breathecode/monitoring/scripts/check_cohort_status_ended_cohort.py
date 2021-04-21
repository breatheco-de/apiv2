#!/usr/bin/env python
"""
Checks if ending date has passed and cohort status is not ended
"""
from breathecode.utils import ScriptNotification
from breathecode.admissions.models import Cohort
from django.utils import timezone

to_fix_cohort_stage = Cohort.objects.filter(ending_date__lt=timezone.now())\
    .exclude(stage='ENDED').values_list('name', flat=True)

if len(to_fix_cohort_stage) > 0:
    to_fix_cohort_name = (", ").join(to_fix_cohort_stage)

    raise ScriptNotification(
        f"These cohorts {to_fix_cohort_name} ended but their stage is different that ENDED", status='MINOR')

print("Everything up to date")
