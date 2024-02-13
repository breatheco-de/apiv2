from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

PENDING = 'PENDING'
DONE = 'DONE'
CANCELLED = 'CANCELLED'
REVERSED = 'REVERSED'
PAUSED = 'PAUSED'
ABORTED = 'ABORTED'
ERROR = 'ERROR'
SCHEDULED = 'SCHEDULED'
TASK_STATUS = (
    (PENDING, 'Pending'),
    (DONE, 'Done'),
    (CANCELLED, 'Cancelled'),
    (REVERSED, 'Reversed'),
    (PAUSED, 'Paused'),
    (ABORTED, 'Aborted'),
    (ERROR, 'Error'),
    (SCHEDULED, 'Scheduled'),
)


class TaskManager(models.Model):
    current_page = models.IntegerField(default=0, blank=True, null=True)
    total_pages = models.IntegerField(default=1, blank=True, null=True)
    attempts = models.IntegerField(default=1)

    task_module = models.CharField(max_length=200)
    task_name = models.CharField(max_length=200)

    reverse_module = models.CharField(max_length=200, blank=True, null=True)
    reverse_name = models.CharField(max_length=200, blank=True, null=True)

    exception_module = models.CharField(max_length=200, blank=True, null=True)
    exception_name = models.CharField(max_length=200, blank=True, null=True)

    arguments = models.JSONField(default=dict, blank=True, null=True)
    status = models.CharField(max_length=20, choices=TASK_STATUS, default=PENDING)
    status_message = models.TextField(blank=True, null=True, max_length=255)
    task_id = models.CharField(max_length=36, default='', blank=True)

    killed = models.BooleanField(default=False)
    last_run = models.DateTimeField()

    started_at = models.DateTimeField(default=None, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.task_module + '.' + self.task_name + ' ' + str(self.arguments)

    def clean(self) -> None:
        if self.started_at is None and self.status == PENDING:
            self.started_at = timezone.now()

        return super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class TaskWatcher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    tasks = models.ManyToManyField(TaskManager,
                                   blank=True,
                                   related_name='watchers',
                                   help_text='Notify for the progress of these tasks')

    email = models.EmailField(blank=True, null=True)

    on_error = models.BooleanField(default=True)
    on_success = models.BooleanField(default=True)
    watch_progress = models.BooleanField(default=False)

    def __str__(self):
        return self.user.email
