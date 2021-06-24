from django.contrib.auth.models import User
from django.db import models
from breathecode.admissions.models import Cohort

PENDING = 'PENDING'
DONE = 'DONE'
TASK_STATUS = (
    (PENDING, 'Pending'),
    (DONE, 'Done'),
)

APPROVED = 'APPROVED'
REJECTED = 'REJECTED'
REVISION_STATUS = (
    (PENDING, 'Pending'),
    (APPROVED, 'Approved'),
    (REJECTED, 'Rejected'),
)

PROJECT = 'PROJECT'
QUIZ = 'QUIZ'
LESSON = 'LESSON'
EXERCISE = 'EXERCISE'
TASK_TYPE = (
    (PROJECT, 'project'),
    (QUIZ, 'quiz'),
    (LESSON, 'lesson'),
    (EXERCISE, 'Exercise'),
)


# Create your models here.
class Task(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    associated_slug = models.SlugField(max_length=150)
    title = models.CharField(max_length=150)

    task_status = models.CharField(max_length=15,
                                   choices=TASK_STATUS,
                                   default=PENDING)
    revision_status = models.CharField(max_length=15,
                                       choices=REVISION_STATUS,
                                       default=PENDING)
    task_type = models.CharField(max_length=15, choices=TASK_TYPE)
    github_url = models.CharField(max_length=150,
                                  blank=True,
                                  default=None,
                                  null=True)
    live_url = models.CharField(max_length=150,
                                blank=True,
                                default=None,
                                null=True)
    description = models.TextField(max_length=450, blank=True)

    cohort = models.ForeignKey(Cohort,
                               on_delete=models.CASCADE,
                               blank=True,
                               null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


class UserProxy(User):
    class Meta:
        proxy = True


class CohortProxy(Cohort):
    class Meta:
        proxy = True
