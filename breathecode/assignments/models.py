from django.contrib.auth.models import User
from django.db import models
from breathecode.admissions.models import Cohort

__all__ = ['UserProxy', 'CohortProxy', 'Task']

PENDING = 'PENDING'
DONE = 'DONE'
TASK_STATUS = (
    (PENDING, 'Pending'),
    (DONE, 'Done'),
)

APPROVED = 'APPROVED'
REJECTED = 'REJECTED'
IGNORED = 'IGNORED'
REVISION_STATUS = (
    (PENDING, 'Pending'),
    (APPROVED, 'Approved'),
    (REJECTED, 'Rejected'),
    (IGNORED, 'Ignored'),
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

    task_status = models.CharField(max_length=15, choices=TASK_STATUS, default=PENDING)
    revision_status = models.CharField(max_length=15, choices=REVISION_STATUS, default=PENDING)
    task_type = models.CharField(max_length=15, choices=TASK_TYPE)
    github_url = models.CharField(max_length=150, blank=True, default=None, null=True)
    live_url = models.CharField(max_length=150, blank=True, default=None, null=True)
    description = models.TextField(max_length=450, blank=True)

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


class UserProxy(User):

    class Meta:
        proxy = True


class CohortProxy(Cohort):

    class Meta:
        proxy = True


PRIVATE = 'PRIVATE'
UNLISTED = 'UNLISTED'
PUBLIC = 'PUBLIC'
VISIBILITY_STATUS = (
    (PRIVATE, 'Private'),
    (UNLISTED, 'Unlisted'),
    (PUBLIC, 'Public'),
)


class FinalProject(models.Model):
    repo_owner = models.ForeignKey(User,
                                   on_delete=models.SET_NULL,
                                   blank=True,
                                   null=True,
                                   related_name='projects_owned')
    name = models.CharField(max_length=150)
    one_line_desc = models.CharField(max_length=150)
    description = models.TextField()

    members = models.ManyToManyField(User, related_name='final_projects')

    project_status = models.CharField(max_length=15,
                                      choices=TASK_STATUS,
                                      default=PENDING,
                                      help_text='Done projects will be reviewed for publication')
    revision_status = models.CharField(
        max_length=15,
        choices=REVISION_STATUS,
        default=PENDING,
        help_text='Only approved projects will display on the feature projects list')
    revision_message = models.TextField(null=True, blank=True, default=None)

    visibility_status = models.CharField(max_length=15,
                                         choices=VISIBILITY_STATUS,
                                         default=PRIVATE,
                                         help_text='Public project will be visible to other users')

    repo_url = models.URLField(blank=True, null=True, default=None)
    public_url = models.URLField(blank=True, null=True, default=None)
    logo_url = models.URLField(blank=True, null=True, default=None)
    slides_url = models.URLField(blank=True, null=True, default=None)
    video_demo_url = models.URLField(blank=True, null=True, default=None)

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
