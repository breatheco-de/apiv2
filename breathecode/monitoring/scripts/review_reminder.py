#!/usr/bin/env python
"""
Checks for recent graduates with NPS > 7 and reminds about asking for reviews
"""

# flake8: noqa: F821

from breathecode.utils import ScriptNotification
from breathecode.feedback.models import Review
from datetime import timedelta
from django.utils import timezone


def calculate_weeks(date_created, current_date):
    days = abs(date_created - current_date).days
    weeks = days // 7
    return weeks


TODAY = timezone.now()
EIGHT_WEEKS_AGO = TODAY - timedelta(weeks=8)

# Cohorts that ended no more than 4 weeks ago
reviews = Review.objects.filter(
    status="PENDING",
    cohort__academy__id=academy.id,
    cohort__ending_date__gte=EIGHT_WEEKS_AGO,
    cohort__kickoff_date__lte=TODAY,
)

call_to_action = (
    f'Click here to <a href="{ADMIN_URL}/growth/reviews?location={academy.slug}">see a more detailed list</a>'
)

help_info = f'🆘 Need help? Learn more about <a href="https://4geeksacademy.notion.site/Student-Reviews-762eb87ae8d84c26b305d7f5c677776f">how reviews work at 4Geeks</a>'

# exclude cohorts that never end
reviews = reviews.exclude(cohort__never_ends=True).exclude(cohort__stage__in=["DELETED", "INACTIVE"])
total_reviews = reviews.count()
if total_reviews == 0:
    print(f"No Pending Reviews for academy {academy.slug}")

else:
    review_names = ("\n").join(
        [
            "- Ask "
            + (
                r.author.first_name
                + " "
                + r.author.last_name
                + " ("
                + str(r.nps_previous_rating if not None else "0")
                + "/10) from "
                + r.cohort.name
                + " to review us at "
                + '<a href="'
                + r.platform.review_signup
                + '">'
                + r.platform.name
                + "</a>"
            )
            for r in reviews
        ]
    )

    raise ScriptNotification(
        f"There are {str(total_reviews)} reviews to be requested because the students gave us 8 or more on the NPS survey: "
        f"\n {review_names} \n\n {call_to_action} \n\n {help_info}",
        status="CRITICAL",
        title=f"There are {str(total_reviews)} reviews pending to be requested at {academy.name}",
        slug="cohort-have-pending-reviews",
    )
