#!/usr/bin/env python
"""
Remind cohort status update after starting date
"""

# flake8: noqa: F821

from breathecode.utils import ScriptNotification
from breathecode.admissions.models import Cohort
from django.utils import timezone

to_fix_cohort_stage = (
    Cohort.objects.filter(kickoff_date__lt=timezone.now(), academy__id=academy.id, stage="PREWORK")
    .exclude(never_ends=True)
    .values_list("name", flat=True)
)

if len(to_fix_cohort_stage) > 0:
    to_fix_cohort_name = ("\n").join(["- " + cohort_name for cohort_name in to_fix_cohort_stage])

    raise ScriptNotification(
        f"These cohorts need to me marked as started or any other further status because the starting date already passed: \n {to_fix_cohort_name} ",
        status="CRITICAL",
        title=f"There are {str(len(to_fix_cohort_stage))} cohort that should be marked as STARTED or further",
        slug="cohort-stage-should-be-started",
    )

else:
    print("All cohort status are consistent with the kickoff date")
