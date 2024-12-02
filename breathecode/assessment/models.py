import binascii
import os
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db import models

from breathecode.admissions.models import Academy

from . import signals

__all__ = ["UserProxy", "Assessment", "Question", "Option", "UserAssessment", "Answer"]


class UserProxy(User):

    class Meta:
        proxy = True


class Assessment(models.Model):

    def __init__(self, *args, **kwargs):
        super(Assessment, self).__init__(*args, **kwargs)
        self.__old_slug = self.slug

    slug = models.SlugField(max_length=200, unique=True)
    title = models.CharField(max_length=255, blank=True)
    lang = models.CharField(max_length=3, blank=True, default="en")

    max_session_duration = models.DurationField(
        default=timedelta(minutes=30), help_text="No more answers will be accepted after X amount of minutes"
    )

    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        default=None,
        blank=True,
        null=True,
        help_text="Not all assesments are triggered by academies",
    )
    author = models.ForeignKey(User, on_delete=models.SET_NULL, default=None, blank=True, null=True)

    private = models.BooleanField(default=False)
    is_archived = models.BooleanField(
        default=False, help_text="If assessments have answers, they cannot be deleted but will be archived instead"
    )

    next = models.URLField(default=None, blank=True, null=True)

    is_instant_feedback = models.BooleanField(
        default=True, help_text="If true, users will know immediately if their answer was correct"
    )

    # the original translation (will only be set if the quiz is a translation of another one)
    original = models.ForeignKey(
        "Assessment",
        on_delete=models.CASCADE,
        related_name="translations",
        default=None,
        blank=True,
        null=True,
        help_text="The original translation (will only be set if the quiz is a translation of another one)",
    )

    comment = models.CharField(max_length=255, default=None, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.slug} ({self.lang})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Only delete assessments without answers
        if self.userassessment_set.count() == 0:
            super().delete(*args, **kwargs)

        # if assessment has answers we dont delete
        self.is_archived = True
        self.save()

    def to_json(self, *args, **kwargs):

        _json = {
            "info": {
                "id": self.id,
                "slug": self.slug,
                "title": self.title,
                "is_instant_feedback": self.is_instant_feedback,
            },
            "questions": [],
        }
        _questions = self.question_set.all()
        for q in _questions:
            _q = {"id": q.id, "title": q.title, "options": []}

            _options = q.option_set.all()
            for o in _options:
                _q["options"].append(
                    {
                        "id": o.id,
                        "title": o.title,
                        "score": o.score,
                    }
                )

            _json["questions"].append(_q)

        return _json


class AssessmentLayout(models.Model):

    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    slug = models.SlugField(max_length=200, unique=True)
    additional_styles = models.TextField(
        blank=True, null=True, default=None, help_text="This stylesheet will be included in the assessment if specified"
    )
    variables = models.JSONField(
        default=None, blank=True, null=True, help_text="Additional params to be passed into the assessment content"
    )

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


class AssessmentThreshold(models.Model):

    assessment = models.ForeignKey(
        "Assessment", on_delete=models.CASCADE, related_name="score_thresholds", default=None, blank=True, null=True
    )

    title = models.CharField(
        max_length=255, default=None, blank=True, null=True, help_text="Title is good for internal use"
    )

    tags = models.CharField(
        max_length=255,
        default=None,
        blank=True,
        null=True,
        help_text="Ideal to group thresholds under a taxonomy, that way you can have several groups of thresholds for the same quiz",
    )

    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        default=None,
        blank=True,
        null=True,
        help_text="If null it will be default, but if specified, the only this academy will have this threshold",
    )

    score_threshold = models.IntegerField(
        help_text="You can set a threshold to determine if the user score is successfull"
    )

    success_message = models.TextField(default=None, blank=True, null=True)
    fail_message = models.TextField(default=None, blank=True, null=True)

    success_next = models.URLField(default=None, blank=True, null=True)
    fail_next = models.URLField(default=None, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


TEXT = "TEXT"
NUMBER = "NUMBER"
SELECT = "SELECT"
SELECT_MULTIPLE = "SELECT_MULTIPLE"
QUESTION_TYPE = (
    (TEXT, "Text"),
    (NUMBER, "Number"),
    (SELECT, "Select"),
    (SELECT_MULTIPLE, "Select Multiple"),
)


class Question(models.Model):
    title = models.TextField()
    help_text = models.CharField(max_length=255, default=None, blank=True, null=True)

    lang = models.CharField(max_length=3, blank=True, default="us")

    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, default=None, blank=True, null=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, default=None, blank=True, null=True)
    question_type = models.CharField(max_length=15, choices=QUESTION_TYPE, default=SELECT)

    is_deleted = models.BooleanField(
        default=False, help_text="Question collected answers cannot not be deleted, they will have this bullet true"
    )

    position = models.IntegerField(default=None, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"Question {self.id}"


class Option(models.Model):
    title = models.TextField()
    help_text = models.CharField(max_length=255, default=None, blank=True, null=True)
    lang = models.CharField(max_length=3, blank=True, default="en")

    is_deleted = models.BooleanField(
        default=False, help_text="Options with collected answers cannot not be deleted, they will have this bullet true"
    )
    position = models.IntegerField(default=None, blank=True, null=True)

    question = models.ForeignKey(Question, on_delete=models.CASCADE, default=None, blank=True, null=True)
    score = models.FloatField(
        help_text="If picked, this value will add up to the total score of the assesment, you can have negative or fractional values"
    )

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"Option {self.id}"


DRAFT = "DRAFT"
SENT = "SENT"
ANSWERED = "ANSWERED"
ERROR = "ERROR"
EXPIRED = "EXPIRED"
SURVEY_STATUS = (
    (DRAFT, "Draft"),
    (SENT, "Sent"),
    (ANSWERED, "Answered"),  # If marked as 'ANSWERED' the total_score will be auto-calculated
    (ERROR, "Error"),
    (EXPIRED, "Expired"),
)


class UserAssessment(models.Model):
    _old_status = None

    title = models.CharField(max_length=200, blank=True)
    lang = models.CharField(max_length=3, blank=True, default="en")

    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, default=None, blank=True, null=True)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, default=None, blank=True, null=True)

    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, default=None, blank=True, null=True, help_text="How is answering the assessment"
    )
    owner_email = models.CharField(
        max_length=150,
        default=None,
        blank=True,
        null=True,
        help_text="If there is not registered owner we can use the email as reference",
    )
    has_marketing_consent = models.BooleanField(default=False)
    conversion_info = models.JSONField(
        default=None, blank=True, null=True, help_text="UTMs and other conversion information."
    )
    phone_regex = RegexValidator(
        regex=r"^\+?1?\d{9,15}$",
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
    )
    owner_phone = models.CharField(
        validators=[phone_regex], max_length=17, blank=True, default=""
    )  # validators should be a list

    total_score = models.FloatField(help_text="Total sum of all chosen options in the assesment")

    opened = models.BooleanField(default=False)
    status = models.CharField(max_length=15, choices=SURVEY_STATUS, default=DRAFT)
    status_text = models.TextField(default=None, blank=True, null=True)

    token = models.CharField(max_length=255, unique=True, help_text="Auto-generated when a user assignment is created")

    comment = models.CharField(max_length=255, default=None, blank=True, null=True)

    started_at = models.DateTimeField(default=None, blank=True, null=True)
    finished_at = models.DateTimeField(default=None, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._old_status = self.status

    def save(self, *args, **kwargs):

        is_creating = self.pk is None
        if not self.pk:
            self.token = binascii.hexlify(os.urandom(20)).decode()

        _instance = super().save(*args, **kwargs)

        # Answer is being closed
        if is_creating or self.status != self._old_status:
            signals.userassessment_status_updated.send_robust(instance=self, sender=self.__class__)

        return _instance

    def get_score(self):

        total_score = 0
        answers = self.answer_set.all().order_by("created_at")
        last_one = None
        for a in answers:
            last_one = a

            # Ignore open text questions
            if a.question.question_type == "TEXT":
                continue
            if a.option:
                a.value = str(a.option.score)

            try:
                total_score += float(a.value)
            except ValueError:
                pass

        return total_score, last_one

    def __str__(self):
        return self.title


class Answer(models.Model):

    user_assessment = models.ForeignKey(UserAssessment, on_delete=models.CASCADE, default=None, blank=True, null=True)

    # Do not implement many-to-many, its better to have many answers, one for each selected option
    option = models.ForeignKey(
        Option,
        on_delete=models.SET_NULL,
        default=None,
        blank=True,
        null=True,
        help_text="Will be null if open question, no options to pick. Or if option was deleted historically",
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE, default=None, blank=True, null=True)
    value = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
