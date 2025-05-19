from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.utils import timezone

from breathecode.admissions.models import Cohort

from . import signals

__all__ = ["UserProxy", "CohortProxy", "Task", "UserAttachment"]


class UserAttachment(models.Model):
    slug = models.SlugField(max_length=150, unique=True)
    name = models.CharField(max_length=150)
    mime = models.CharField(max_length=120)
    url = models.URLField(max_length=255)
    hash = models.CharField(max_length=64)

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.name} ({self.id})"


class AssignmentTelemetry(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    asset_slug = models.CharField(max_length=200)
    telemetry = models.JSONField(
        null=True, blank=True, default=None, help_text="Incoming JSON from LearnPack with detailed telemetry info"
    )

    engagement_score = models.FloatField(
        null=True, blank=True, default=None, help_text="Calculated score from 0 to 100 based on the telemetry"
    )

    frustration_score = models.FloatField(
        null=True, blank=True, default=None, help_text="Calculated score 0 to 100 based on the telemetry"
    )
    metrics_algo_version = models.FloatField(
        null=True, blank=True, default=None, help_text="Version of the algorithm used to calculate the metrics"
    )
    metrics = models.JSONField(
        null=True, blank=True, default=None, help_text="Calculated metrics based on the telemetry"
    )
    total_time = models.DurationField(null=True, blank=True, default=None, help_text="Total time spent on the exercise")
    completion_rate = models.FloatField(
        null=True, blank=True, default=None, help_text="Completion rate from 0 to 100 of the exercise in percentage"
    )

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


PENDING = "PENDING"
DONE = "DONE"


PROJECT = "PROJECT"
QUIZ = "QUIZ"
LESSON = "LESSON"
EXERCISE = "EXERCISE"
TASK_TYPE = (
    (PROJECT, "project"),
    (QUIZ, "quiz"),
    (LESSON, "lesson"),
    (EXERCISE, "Exercise"),
)


class TaskStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    DONE = "DONE", "Done"


class RevisionStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    IGNORED = "IGNORED", "Ignored"


# Create your models here.
class Task(models.Model):
    TaskStatus = TaskStatus
    RevisionStatus = RevisionStatus

    class TaskType(models.TextChoices):
        PROJECT = "PROJECT", "project"
        QUIZ = "QUIZ", "quiz"
        LESSON = "LESSON", "lesson"
        EXERCISE = "EXERCISE", "Exercise"

    _current_task_status = None
    _current_revision_status = None

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    telemetry = models.ForeignKey(
        AssignmentTelemetry,
        on_delete=models.CASCADE,
        default=None,
        null=True,
        blank=True,
        help_text="Learnpack telemetry json will be stored and shared among all the assignments form the same associalted_slug",
    )

    associated_slug = models.SlugField(max_length=150, db_index=True)
    title = models.CharField(max_length=150, db_index=True)

    rigobot_repository_id = models.IntegerField(null=True, blank=True, default=None, db_index=True)

    task_status = models.CharField(max_length=15, choices=TaskStatus, default=TaskStatus.PENDING, db_index=True)
    revision_status = models.CharField(
        max_length=15, choices=RevisionStatus, default=RevisionStatus.PENDING, db_index=True
    )
    task_type = models.CharField(max_length=15, choices=TaskType, db_index=True)
    github_url = models.CharField(max_length=150, blank=True, default=None, null=True)
    live_url = models.CharField(max_length=150, blank=True, default=None, null=True)
    description = models.TextField(max_length=450, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True, default=None, db_index=True)

    delivered_flags = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="JSON array of JWT-like tokens for flag validation in CTF challenges",
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        db_index=True,
        help_text="The moment when the student checked the revision",
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        db_index=True,
        help_text="The moment when the teacher marks the task as ACCEPTED or REJECTED",
    )
    delivered_at = models.DateTimeField(null=True, blank=True, default=None, db_index=True)

    subtasks = models.JSONField(
        default=None,
        blank=True,
        null=True,
        help_text="If readme contains checkboxes they will be converted into substasks and this json will kep track of completition",
    )

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, blank=True, null=True)

    attachments = models.ManyToManyField(UserAttachment, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_task_status = self.task_status
        self._current_revision_status = self.revision_status

    # def clean(self):
    #     if self.cohort is None:
    #         raise forms.ValidationError('Cohort is required')

    def save(self, *args, **kwargs):
        # check the fields before saving
        self.full_clean()

        creating = not self.pk

        # Set reviewed_at when revision status changes to REJECTED or APPROVED
        if not creating and self.revision_status != self._current_revision_status:
            if self.revision_status in [self.RevisionStatus.REJECTED, self.RevisionStatus.APPROVED]:
                self.reviewed_at = timezone.now()

        super().save(*args, **kwargs)
        if not creating and self.task_status != self._current_task_status:
            signals.assignment_status_updated.delay(instance=self, sender=self.__class__)

        if not creating and self.revision_status != self._current_revision_status:
            signals.revision_status_updated.delay(instance=self, sender=self.__class__)

        # only validate this on creation
        if creating:
            signals.assignment_created.delay(instance=self, sender=self.__class__)

        self._current_task_status = self.task_status
        self._current_revision_status = self.revision_status


class UserProxy(User):

    class Meta:
        proxy = True


class CohortProxy(Cohort):

    class Meta:
        proxy = True


PRIVATE = "PRIVATE"
UNLISTED = "UNLISTED"
PUBLIC = "PUBLIC"
VISIBILITY_STATUS = (
    (PRIVATE, "Private"),
    (UNLISTED, "Unlisted"),
    (PUBLIC, "Public"),
)


class FinalProject(models.Model):
    TaskStatus = TaskStatus

    repo_owner = models.ForeignKey(
        User, on_delete=models.SET_NULL, blank=True, null=True, related_name="projects_owned"
    )
    name = models.CharField(max_length=150)
    one_line_desc = models.CharField(max_length=150)
    description = models.TextField()

    members = models.ManyToManyField(User, related_name="final_projects")

    project_status = models.CharField(
        max_length=15,
        choices=TaskStatus,
        default=TaskStatus.PENDING,
        help_text="Done projects will be reviewed for publication",
    )
    revision_status = models.CharField(
        max_length=15,
        choices=RevisionStatus,
        default=RevisionStatus.PENDING,
        help_text="Only approved projects will display on the feature projects list",
    )
    revision_message = models.TextField(null=True, blank=True, default=None)

    visibility_status = models.CharField(
        max_length=15,
        choices=VISIBILITY_STATUS,
        default=PRIVATE,
        help_text="Public project will be visible to other users",
    )

    repo_url = models.URLField(blank=True, null=True, default=None)
    public_url = models.URLField(blank=True, null=True, default=None)
    logo_url = models.URLField(blank=True, null=True, default=None)
    screenshot = models.URLField(blank=True, null=True, default=None)
    slides_url = models.URLField(blank=True, null=True, default=None)
    video_demo_url = models.URLField(blank=True, null=True, default=None)

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


ERROR = "ERROR"
IGNORED = "IGNORED"
LEARNPACK_WEBHOOK_STATUS = (
    (PENDING, "Pending"),
    (DONE, "Done"),
    (IGNORED, "Ignored"),
    (ERROR, "Error"),
)


class LearnPackWebhook(models.Model):

    is_streaming = models.BooleanField()
    event = models.CharField(max_length=15)
    payload = models.JSONField(blank=True, null=True, default=None, help_text="Will be set by learnpack")
    student = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, default=None)
    telemetry = models.ForeignKey(AssignmentTelemetry, on_delete=models.CASCADE, blank=True, null=True, default=None)

    status = models.CharField(max_length=9, choices=LEARNPACK_WEBHOOK_STATUS, default=PENDING)
    status_text = models.TextField(default=None, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    # def __str__(self):
    #     return f'Learnpack event {self.event} {self.status} => Student: {self.student.id}'


class Provider(models.TextChoices):
    GITHUB = "GITHUB", "GitHub"


class RepositoryDeletionOrder(models.Model):
    Provider = Provider

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ERROR = "ERROR", "Error"
        DELETED = "DELETED", "Deleted"
        TRANSFERRED = "TRANSFERRED", "Transferred"
        NO_STARTED = "NO_STARTED", "No started"
        TRANSFERRING = "TRANSFERRING", "Transferring"
        CANCELLED = "CANCELLED", "Cancelled"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._status = self.status

    provider = models.CharField(max_length=15, choices=Provider, default=Provider.GITHUB)
    status = models.CharField(max_length=15, choices=Status, default=Status.PENDING)
    status_text = models.TextField(default=None, null=True, blank=True)

    repository_user = models.CharField(max_length=256)
    repository_name = models.CharField(max_length=256)

    notified_at = models.DateTimeField(default=None, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, default=None)

    starts_transferring_at = models.DateTimeField(default=None, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def clean(self):
        if self.status == RepositoryDeletionOrder.Status.TRANSFERRING:
            self.starts_transferring_at = timezone.now()

    def save(self, *args, **kwargs):
        from .signals import status_updated

        self.full_clean()
        is_created = not self.pk

        super().save(*args, **kwargs)

        if (self.status != self._status or is_created) and self.status == RepositoryDeletionOrder.Status.TRANSFERRING:
            status_updated.delay(sender=self.__class__, instance=self)

        self._status = self.status


class RepositoryWhiteList(models.Model):
    Provider = Provider

    provider = models.CharField(max_length=15, choices=Provider, default=Provider.GITHUB)
    repository_user = models.CharField(max_length=256)
    repository_name = models.CharField(max_length=256)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

        RepositoryDeletionOrder.objects.filter(
            provider=self.provider,
            repository_user__iexact=self.repository_user,
            repository_name__iexact=self.repository_name,
        ).exclude(
            Q(status=RepositoryDeletionOrder.Status.DELETED) | Q(status=RepositoryDeletionOrder.Status.CANCELLED)
        ).delete()
