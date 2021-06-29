from django.db import models
from django.contrib.auth.models import User
from breathecode.admissions.models import Academy, Cohort
from breathecode.events.models import Event


class UserProxy(User):
    class Meta:
        proxy = True


class Assessment(models.Model):
    slug = models.SlugField(max_length=200, primary_key=True)
    title = models.CharField(max_length=255, blank=True)
    lang = models.CharField(max_length=3, blank=True, default='en')

    score_threshold = models.IntegerField(
        default=None,
        blank=True,
        null=True,
        help_text=
        "You can set a threshold to determine if the user score is successfull"
    )
    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        default=None,
        blank=True,
        null=True,
        help_text="Not all assesments are triggered by academies")
    author = models.ForeignKey(User,
                               on_delete=models.SET_NULL,
                               default=None,
                               blank=True,
                               null=True)

    private = models.BooleanField(default=False)

    # the original translation (will only be set if the quiz is a translation of anotherone)
    original = models.ForeignKey(
        'Assessment',
        on_delete=models.CASCADE,
        related_name="translations",
        default=None,
        blank=True,
        null=True,
        help_text=
        "The original translation (will only be set if the quiz is a translation of anotherone)"
    )

    comment = models.CharField(max_length=255,
                               default=None,
                               blank=True,
                               null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


TEXT = 'TEXT'
NUMBER = 'NUMBER'
SELECT = 'SELECT'
SELECT_MULTIPLE = 'SELECT_MULTIPLE'
QUESTION_TYPE = (
    (TEXT, 'Text'),
    (NUMBER, 'Number'),
    (SELECT, 'Select'),
    (SELECT_MULTIPLE, 'Select Multiple'),
)


class Question(models.Model):
    title = models.TextField()
    help_text = models.CharField(max_length=255,
                                 default=None,
                                 blank=True,
                                 null=True)
    lang = models.CharField(max_length=3, blank=True, default='en')

    assessment = models.ForeignKey(Assessment,
                                   on_delete=models.CASCADE,
                                   default=None,
                                   blank=True,
                                   null=True)
    author = models.ForeignKey(User,
                               on_delete=models.SET_NULL,
                               default=None,
                               blank=True,
                               null=True)
    question_type = models.CharField(max_length=15,
                                     choices=QUESTION_TYPE,
                                     default=SELECT)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


class Option(models.Model):
    title = models.TextField()
    help_text = models.CharField(max_length=255,
                                 default=None,
                                 blank=True,
                                 null=True)
    lang = models.CharField(max_length=3, blank=True, default='en')

    question = models.ForeignKey(Question,
                                 on_delete=models.CASCADE,
                                 default=None,
                                 blank=True,
                                 null=True)
    score = models.FloatField(
        help_text=
        "If picked, this value will add up to the total score of the assesment, you can have negative or fractional values"
    )

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


DRAFT = 'DRAFT'
SENT = 'SENT'
ANSWERED = 'ANSWERED'
EXPIRED = 'EXPIRED'
SURVEY_STATUS = (
    (DRAFT, 'DRAFT'),
    (SENT, 'Sent'),
    (EXPIRED, 'Expired'),
)


class UserAssessment(models.Model):
    title = models.CharField(max_length=200, blank=True)
    lang = models.CharField(max_length=3, blank=True, default='en')

    academy = models.ForeignKey(Academy,
                                on_delete=models.CASCADE,
                                default=None,
                                blank=True,
                                null=True)
    assessment = models.ForeignKey(Assessment,
                                   on_delete=models.CASCADE,
                                   default=None,
                                   blank=True,
                                   null=True)
    owner = models.ForeignKey(User,
                              on_delete=models.CASCADE,
                              default=None,
                              blank=True,
                              null=True)

    total_score = models.FloatField(
        help_text="Total sum of all chosen options in the assesment")

    opened = models.BooleanField(default=False)
    status = models.CharField(max_length=15,
                              choices=SURVEY_STATUS,
                              default=DRAFT)

    comment = models.CharField(max_length=255,
                               default=None,
                               blank=True,
                               null=True)

    started_at = models.DateTimeField(default=None, blank=True, null=True)
    finished_at = models.DateTimeField(default=None, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


class Answer(models.Model):

    user_assesment = models.ForeignKey(UserAssessment,
                                       on_delete=models.CASCADE,
                                       default=None,
                                       blank=True,
                                       null=True)
    option = models.ForeignKey(
        Option,
        on_delete=models.CASCADE,
        default=None,
        blank=True,
        null=True,
        help_text="Will be null if open question, no options to pick")
    question = models.ForeignKey(Question,
                                 on_delete=models.CASCADE,
                                 default=None,
                                 blank=True,
                                 null=True)
    value = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
