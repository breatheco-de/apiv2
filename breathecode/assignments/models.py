from django.contrib.auth.models import User
from django.db import models
from . import signals
from breathecode.admissions.models import Cohort

__all__ = ['UserProxy', 'CohortProxy', 'Task', 'UserAttachment']


class UserAttachment(models.Model):
    slug = models.SlugField(max_length=150, unique=True)
    name = models.CharField(max_length=150)
    mime = models.CharField(max_length=60)
    url = models.URLField(max_length=255)
    hash = models.CharField(max_length=64)

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.name} ({self.id})'


class AssignmentTelemetry(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    asset_slug = models.CharField(max_length=200)
    telemetry = models.JSONField(null=True,
                                 blank=True,
                                 default=None,
                                 help_text='Incoming JSON from LearnPack with detailed telemetry info')

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


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
    _current_task_status = None

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    telemetry = models.ForeignKey(
        AssignmentTelemetry,
        on_delete=models.CASCADE,
        default=None,
        null=True,
        blank=True,
        help_text=
        'Learnpack telemetry json will be stored and shared among all the assignments form the same associalted_slug')

    associated_slug = models.SlugField(max_length=150, db_index=True)
    title = models.CharField(max_length=150, db_index=True)

    rigobot_repository_id = models.IntegerField(null=True, blank=True, default=None, db_index=True)

    task_status = models.CharField(max_length=15, choices=TASK_STATUS, default=PENDING, db_index=True)
    revision_status = models.CharField(max_length=15, choices=REVISION_STATUS, default=PENDING, db_index=True)
    task_type = models.CharField(max_length=15, choices=TASK_TYPE, db_index=True)
    github_url = models.CharField(max_length=150, blank=True, default=None, null=True)
    live_url = models.CharField(max_length=150, blank=True, default=None, null=True)
    description = models.TextField(max_length=450, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True, default=None, db_index=True)
    delivered_at = models.DateTimeField(null=True, blank=True, default=None, db_index=True)

    subtasks = models.JSONField(
        default=None,
        blank=True,
        null=True,
        help_text=
        'If readme contains checkboxes they will be converted into substasks and this json will kep track of completition'
    )

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, blank=True, null=True)

    attachments = models.ManyToManyField(UserAttachment, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_task_status = self.task_status

    def save(self, *args, **kwargs):
        # check the fields before saving
        self.full_clean()

        creating = not self.pk

        super().save(*args, **kwargs)

        if not creating and self.task_status != self._current_task_status:
            signals.assignment_status_updated.send(instance=self, sender=self.__class__)

        # only validate this on creation
        if creating:
            signals.assignment_created.send(instance=self, sender=self.__class__)

        self._current_task_status = self.task_status


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
    revision_status = models.CharField(max_length=15,
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
    screenshot = models.URLField(blank=True, null=True, default=None)
    slides_url = models.URLField(blank=True, null=True, default=None)
    video_demo_url = models.URLField(blank=True, null=True, default=None)

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


# PENDING = 'PENDING'
# DONE = 'DONE'
ERROR = 'ERROR'
LEARNPACK_WEBHOOK_STATUS = (
    (PENDING, 'Pending'),
    (DONE, 'Done'),
    (ERROR, 'Error'),
)


class LearnPackWebhook(models.Model):

    is_streaming = models.BooleanField()
    event = models.CharField(max_length=15)
    payload = models.JSONField(blank=True, null=True, default=None, help_text='Will be set by learnpack')
    student = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, default=None)
    telemetry = models.ForeignKey(AssignmentTelemetry, on_delete=models.CASCADE, blank=True, null=True, default=None)

    status = models.CharField(max_length=9, choices=LEARNPACK_WEBHOOK_STATUS, default=PENDING)
    status_text = models.TextField(default=None, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    # def __str__(self):
    #     return f'Learnpack event {self.event} {self.status} => Student: {self.student.id}'
