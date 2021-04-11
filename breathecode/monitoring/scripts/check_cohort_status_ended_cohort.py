#!/usr/bin/env python
"""
Checks if ending date has passed and cohort status is not ended
"""
from breathecode.utils import ScriptNotification
from breathecode.admissions.models import Cohort
from django.utils import timezone

cohorts = Cohort.objects.filter(ending_date__lt=timezone.now())
to_fix_cohort_stage = []

for cohort in cohorts:
    if (cohort.stage != "ENDED"):
        to_fix_cohort_stage.append(cohort.name)

if len(cohorts) > 0:
    to_fix_cohort_name = (", ").join(to_fix_cohort_stage)

    raise ScriptNotification(
        f"These cohorts {to_fix_cohort_name} ended but their stage is different that ENDED", status='MINOR')
else:
    print("Everything up to date")
