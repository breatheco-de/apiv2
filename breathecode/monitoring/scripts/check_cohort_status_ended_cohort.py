#!/usr/bin/env python
"""
Checks if ending date has passed and cohort status is not ended
"""

# flake8: noqa: F821

from breathecode.utils import ScriptNotification
from breathecode.admissions.models import Cohort
from django.utils import timezone

to_fix_cohort_stage = (
    Cohort.objects.filter(ending_date__lt=timezone.now(), academy__id=academy.id)
    .exclude(stage__in=["ENDED", "DELETED"])
    .values_list("name", flat=True)
)

if len(to_fix_cohort_stage) > 0:
    to_fix_cohort_name = ("\n").join(["- " + cohort_name for cohort_name in to_fix_cohort_stage])

    raise ScriptNotification(
        f"These cohorts ended but their stage is different that ENDED: \n {to_fix_cohort_name} ",
        status="CRITICAL",
        title=f"There are {str(len(to_fix_cohort_stage))} cohorts that should be marked as ENDED",
        slug="cohort-stage-should-be-ended",
    )

else:
    print("Everything up to date")
