import datetime
from django.db import models
from django.contrib.auth.models import User
from breathecode.admissions.models import Academy, Cohort, CohortUser
from breathecode.events.models import Event
from breathecode.mentorship.models import MentorshipSession
import breathecode.feedback.signals as signals
from breathecode.authenticate.models import Token

__all__ = ['UserProxy', 'CohortUserProxy', 'CohortProxy', 'Survey', 'Answer']


class UserProxy(User):
    class Meta:
        proxy = True


class CohortUserProxy(CohortUser):
    class Meta:
        proxy = True


class CohortProxy(Cohort):
    class Meta:
        proxy = True


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
    """
    Multiple questions/answers for one single person, surveys can only be send to entire cohorts and they will ask all the possible questions involved in a cohort
    1. How is your teacher?
    2. How is the academy?
    3. How is the blabla..
    """

    lang = models.CharField(max_length=3, blank=True, default='en')

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE)

    max_assistants_to_ask = models.IntegerField(default=2)
    max_teachers_to_ask = models.IntegerField(default=1)

    avg_score = models.CharField(max_length=250,
                                 default=None,
                                 blank=True,
                                 null=True,
                                 help_text='The avg from all the answers taken under this survey',
                                 editable=False)

    response_rate = models.FloatField(default=None, blank=True, null=True)

    status = models.CharField(max_length=15, choices=SURVEY_STATUS, default=PENDING)
    status_json = models.JSONField(default=None, null=True, blank=True)

    duration = models.DurationField(default=datetime.timedelta(hours=24),
                                    help_text='No one will be able to answer after this period of time')
    created_at = models.DateTimeField(auto_now_add=True, editable=True)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    sent_at = models.DateTimeField(default=None, null=True, blank=True)

    def __str__(self):
        return 'Survey for ' + self.cohort.name


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
    def __init__(self, *args, **kwargs):
        super(Answer, self).__init__(*args, **kwargs)
        self.__old_status = self.status

    title = models.CharField(max_length=200, blank=True)
    lowest = models.CharField(max_length=50, default='not likely')
    highest = models.CharField(max_length=50, default='very likely')
    lang = models.CharField(max_length=3, blank=True, default='en')

    event = models.ForeignKey(Event, on_delete=models.SET_NULL, default=None, blank=True, null=True)
    mentorship_session = models.ForeignKey(MentorshipSession,
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
    cohort = models.ForeignKey(Cohort, on_delete=models.SET_NULL, default=None, blank=True, null=True)
    academy = models.ForeignKey(Academy, on_delete=models.SET_NULL, default=None, blank=True, null=True)
    token = models.OneToOneField(Token, on_delete=models.SET_NULL, default=None, blank=True, null=True)

    score = models.IntegerField(default=None, blank=True, null=True)
    comment = models.TextField(max_length=1000, default=None, blank=True, null=True)

    survey = models.ForeignKey(
        Survey,
        on_delete=models.SET_NULL,
        default=None,
        blank=True,
        null=True,
        help_text=
        'You can group one or more answers in one survey, the survey does not belong to any student in particular but answers belong to the student that answered'
    )

    status = models.CharField(max_length=15, choices=SURVEY_STATUS, default=PENDING)

    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None, blank=True, null=True)

    opened_at = models.DateTimeField(default=None, blank=True, null=True)
    sent_at = models.DateTimeField(default=None, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)  # Call the "real" save() method.

        if self.__old_status != self.status and self.status == 'ANSWERED':
            # signal the updated answer
            signals.survey_answered.send(instance=self, sender=Answer)


class ReviewPlatform(models.Model):
    """
    Websites like KareerKarma, Switchup, Coursereport, etc.
    """
    slug = models.SlugField(primary_key=True)
    name = models.CharField(max_length=100)
    website = models.URLField()
    review_signup = models.URLField(blank=True,
                                    null=True,
                                    default=None,
                                    help_text='Give URL to create a new review')
    contact_email = models.EmailField()
    contact_name = models.EmailField(blank=True, null=True, default=None)
    contact_phone = models.CharField(max_length=17, blank=True, null=True, default=None)

    def __str__(self):
        return f'{self.slug}'


PENDING = 'PENDING'
REQUESTED = 'REQUESTED'
DONE = 'DONE'
IGNORE = 'IGNORE'
REVIEW_STATUS = (
    (PENDING, 'Pending'),
    (REQUESTED, 'Requested'),
    (DONE, 'Done'),
    (IGNORE, 'Ignore'),
)


class Review(models.Model):

    nps_previous_rating = models.FloatField(
        blank=True,
        null=True,
        default=None,
        help_text='Automatically calculated based on NPS survey responses')
    total_rating = models.FloatField(blank=True, null=True, default=None)
    public_url = models.URLField(blank=True, null=True, default=None)

    status = models.CharField(max_length=9,
                              choices=REVIEW_STATUS,
                              default=PENDING,
                              help_text='Deleted reviews hav status=Ignore')
    status_text = models.CharField(max_length=255, default=None, null=True, blank=True)
    comments = models.TextField(default=None,
                                null=True,
                                blank=True,
                                help_text='Student comments when leaving the review')

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, null=True, blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    platform = models.ForeignKey(ReviewPlatform, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        cohort = 'no specific cohort'
        if self.cohort is not None:
            cohort = self.cohort.slug
        return f'{self.author.first_name} {self.author.last_name} for {cohort}'
