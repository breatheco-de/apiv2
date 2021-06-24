import datetime
from django.db import models
from django.contrib.auth.models import User
from breathecode.admissions.models import Academy, Cohort, CohortUser
from breathecode.events.models import Event
from breathecode.authenticate.models import Token


class UserProxy(User):
    class Meta:
        proxy = True


class CohortUserProxy(CohortUser):
    class Meta:
        proxy = True


class CohortProxy(Cohort):
    class Meta:
        proxy = True


"""
Multiple questions/answers for one single person, survays can only be send to entire cohorts and they will ask all the possible questions involved in a cohort
1. How is your teacher?
2. How is the academy?
3. How is the blabla..
"""
PENDING = 'PENDING'
SENT = 'SENT'
PARTIAL = 'PARTIAL'
FATAL = 'FATAL'
SURVEY_STATUS = (
    (SENT, 'Sent'),
    (PENDING, 'Pending'),
    (PARTIAL, 'Partial'),
    (FATAL, 'Fatal'),
)


class Survey(models.Model):

    lang = models.CharField(max_length=3, blank=True, default='en')

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE)

    max_assistants_to_ask = models.IntegerField(default=2)
    max_teachers_to_ask = models.IntegerField(default=1)

    avg_score = models.CharField(
        max_length=250,
        default=None,
        blank=True,
        null=True,
        help_text="The avg from all the answers taken under this survey",
        editable=False)

    status = models.CharField(max_length=15,
                              choices=SURVEY_STATUS,
                              default=PENDING)
    status_json = models.JSONField(default=None, null=True, blank=True)

    duration = models.DurationField(
        default=datetime.timedelta(hours=24),
        help_text="No one will be able to answer after this period of time")
    created_at = models.DateTimeField(auto_now_add=True, editable=True)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    sent_at = models.DateTimeField(default=None, null=True, blank=True)

    def __str__(self):
        return "Survey for " + self.cohort.name


PENDING = 'PENDING'
SENT = 'SENT'
ANSWERED = 'ANSWERED'
OPENED = 'OPENED'
EXPIRED = 'EXPIRED'
SURVEY_STATUS = (
    (PENDING, 'Pending'),
    (SENT, 'Sent'),
    (ANSWERED, 'Answered'),
    (OPENED, 'Opened'),
    (EXPIRED, 'Expired'),
)


class Answer(models.Model):
    title = models.CharField(max_length=200, blank=True)
    lowest = models.CharField(max_length=50, default='not likely')
    highest = models.CharField(max_length=50, default='very likely')
    lang = models.CharField(max_length=3, blank=True, default='en')

    event = models.ForeignKey(Event,
                              on_delete=models.SET_NULL,
                              default=None,
                              blank=True,
                              null=True)
    mentor = models.ForeignKey(User,
                               related_name='mentor_set',
                               on_delete=models.SET_NULL,
                               default=None,
                               blank=True,
                               null=True)
    cohort = models.ForeignKey(Cohort,
                               on_delete=models.SET_NULL,
                               default=None,
                               blank=True,
                               null=True)
    academy = models.ForeignKey(Academy,
                                on_delete=models.SET_NULL,
                                default=None,
                                blank=True,
                                null=True)
    token = models.OneToOneField(Token,
                                 on_delete=models.SET_NULL,
                                 default=None,
                                 blank=True,
                                 null=True)

    score = models.CharField(max_length=250,
                             default=None,
                             blank=True,
                             null=True)
    comment = models.TextField(max_length=1000,
                               default=None,
                               blank=True,
                               null=True)

    survey = models.ForeignKey(
        Survey,
        on_delete=models.SET_NULL,
        default=None,
        blank=True,
        null=True,
        help_text=
        'You can group one or more answers in one survey, the survey does not belong to any student in particular but answers belong to the student that answered'
    )

    status = models.CharField(max_length=15,
                              choices=SURVEY_STATUS,
                              default=PENDING)

    user = models.ForeignKey(User,
                             on_delete=models.CASCADE,
                             default=None,
                             blank=True,
                             null=True)

    opened_at = models.DateTimeField(default=None, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
