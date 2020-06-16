from django.contrib.auth.models import User
from django.db import models

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
REPLIT = 'REPLIT'
TASK_TYPE = (
    (PROJECT, 'project'),
    (QUIZ, 'quiz'),
    (LESSON, 'lesson'),
    (REPLIT, 'replit'),
)
# Create your models here.
class Task(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    associated_slug = models.CharField(max_length=150, unique=True)
    title = models.CharField(max_length=150)

    task_status = models.CharField(max_length=15, choices=TASK_STATUS, default=PENDING)
    revision_status = models.CharField(max_length=15, choices=REVISION_STATUS)
    task_type = models.CharField(max_length=15, choices=TASK_TYPE)
    github_url = models.CharField(max_length=150, default=True, null=True)
    live_url = models.CharField(max_length=150, default=True, null=True)
    description = models.TextField(max_length=450)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)