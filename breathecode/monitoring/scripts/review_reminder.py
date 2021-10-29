#!/usr/bin/env python
"""
Checks for recent graduates with NPS > 7 and reminds about asking for reviews
"""
from breathecode.utils import ScriptNotification
from breathecode.feedback.models import Survey, Review
from breathecode.admissions.models import Cohort, Academy
from datetime import datetime, timedelta
from django.utils import timezone


def calculate_weeks(date_created, current_date):
    days = abs(date_created - current_date).days
    weeks = days // 7
    return weeks


TODAY = timezone.now()
EIGHT_WEEKS_AGO = TODAY - timedelta(weeks=8)

# Cohorts that ended no more than 4 weeks ago
reviews = Review.objects.filter(status='PENDING',
                                cohort__academy__id=academy.id,
                                cohort__ending_date__gte=EIGHT_WEEKS_AGO,
                                cohort__kickoff_date__lte=TODAY)

# exclude cohorts that never end
reviews = reviews.exclude(cohort__never_ends=True).exclude(cohort__stage__in=['DELETED', 'INACTIVE'])
total_reviews = reviews.count()
if total_reviews == 0:
    print(f'No Pending Reviews for academy {academy.slug}')

else:
    review_names = ('\n').join([
        '- ' + (r.author.first_name + ' ' + r.author.last_name + ' (' +
                str(r.nps_previous_rating if not None else '0') + '/10) for ' + r.cohort.name + ' in ' +
                r.platform.name) for r in reviews
    ])

    raise ScriptNotification(
        f'There are {str(total_reviews)} reviews to be requested because the students gave us 8 or more on the NPS survey: '
        f'\n {review_names}',
        status='CRITICAL',
        title=f'There are {str(total_reviews)} reviews pending to be requested',
        slug='cohort-have-pending-reviews')
