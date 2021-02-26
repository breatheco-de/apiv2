from django.db import models
from django.contrib.auth.models import User
from breathecode.admissions.models import Academy, Cohort
from breathecode.events.models import Event

class UserProxy(User):
    class Meta:
        proxy = True
class CohortProxy(Cohort):
    class Meta:
        proxy = True

class Assessment(models.Model):
    title = models.CharField(max_length=200, blank=True)
    lang = models.CharField(max_length=3, blank=True, default='en')

    score_threshold = models.IntegerField(default=None, blank=True, null=True, help_text="You can set a threshold to determine if the user score is successfull")
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, default=None, blank=True, null=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, default=None, blank=True, null=True)

    comment = models.CharField(max_length=255, default=None, blank=True, null=True)

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
    title = models.CharField(max_length=200, blank=True)
    help_text = models.CharField(max_length=255, default=None, blank=True, null=True)
    lang = models.CharField(max_length=3, blank=True, default='en')

    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, default=None, blank=True, null=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, default=None, blank=True, null=True)
    question_type = models.CharField(max_length=15, choices=QUESTION_TYPE, default=SELECT)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


class Option(models.Model):
    title = models.CharField(max_length=200, blank=True)
    help_text = models.CharField(max_length=255, default=None, blank=True, null=True)
    lang = models.CharField(max_length=3, blank=True, default='en')

    question = models.ForeignKey(Question, on_delete=models.CASCADE, default=None, blank=True, null=True)
    value = models.CharField(max_length=200)

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
class StudentAssessment(models.Model):
    title = models.CharField(max_length=200, blank=True)
    lang = models.CharField(max_length=3, blank=True, default='en')

    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, default=None, blank=True, null=True)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, default=None, blank=True, null=True)
    student = models.ForeignKey(User, on_delete=models.CASCADE, default=None, blank=True, null=True)

    opened = models.BooleanField(default=False)
    status = models.CharField(max_length=15, choices=SURVEY_STATUS, default=DRAFT)

    comment = models.CharField(max_length=255, default=None, blank=True, null=True)

    started_at = models.DateTimeField(default=None, blank=True, null=True)
    finished_at = models.DateTimeField(default=None, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

class Answer(models.Model):
    # TODO: missing one S? maybe we should update this name and GenerateModelsMixin
    student_assesment = models.ForeignKey(StudentAssessment, on_delete=models.CASCADE, default=None, blank=True, null=True)
    value = models.CharField(max_length=200)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
