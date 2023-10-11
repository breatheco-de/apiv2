from django.db import models

PENDING = 'PENDING'
DONE = 'DONE'
CANCELLED = 'CANCELLED'
REVERSED = 'REVERSED'
PAUSED = 'PAUSED'
ABORTED = 'ABORTED'
ERROR = 'ERROR'
TASK_STATUS = (
    (PENDING, 'Pending'),
    (DONE, 'Done'),
    (CANCELLED, 'Cancelled'),
    (REVERSED, 'Reversed'),
    (PAUSED, 'Paused'),
    (ABORTED, 'Aborted'),
    (ERROR, 'Error'),
)


class TaskManager(models.Model):
    current_page = models.IntegerField(default=0, blank=True, null=True)
    total_pages = models.IntegerField(default=0, blank=True, null=True)
    attemps = models.IntegerField(default=1)

    task_module = models.CharField(max_length=200)
    task_name = models.CharField(max_length=200)

    reverse_module = models.CharField(max_length=200, blank=True, null=True)
    reverse_name = models.CharField(max_length=200, blank=True, null=True)

    arguments = models.JSONField(default=dict, blank=True, null=True)
    status = models.CharField(max_length=20, choices=TASK_STATUS, default=PENDING)
    status_message = models.TextField(blank=True, null=True, max_length=255)

    killed = models.BooleanField(default=False)
    last_run = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.task_module + '.' + self.task_name + ' ' + str(self.arguments)
