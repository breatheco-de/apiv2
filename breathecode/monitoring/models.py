from django.db import models
from django.contrib.auth.models import User
from breathecode.admissions.models import Academy
from breathecode.notify.models import SlackChannel
from datetime import timedelta

LOADING = 'LOADING'
OPERATIONAL = 'OPERATIONAL'
MINOR = 'MINOR'
CRITICAL = 'CRITICAL'
STATUS = (
    (LOADING, 'Loading'),
    (OPERATIONAL, 'Operational'),
    (MINOR, 'Minor'),
    (CRITICAL, 'Critical'),
)


class Application(models.Model):
    title = models.CharField(max_length=100)

    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    status_text = models.CharField(max_length=255,
                                   default=None,
                                   null=True,
                                   blank=True)
    notify_email = models.CharField(max_length=255,
                                    blank=True,
                                    default=None,
                                    null=True)
    notify_slack_channel = models.ForeignKey(
        SlackChannel,
        on_delete=models.SET_NULL,
        blank=True,
        default=None,
        null=True,
        help_text=
        "Please pick an academy first to be able to see the available slack channels to notify"
    )

    status = models.CharField(max_length=20,
                              choices=STATUS,
                              default=OPERATIONAL)

    paused_until = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        help_text='if you want to stop checking for a period of time')

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.title


class Endpoint(models.Model):

    url = models.CharField(max_length=255)
    test_pattern = models.CharField(
        max_length=100,
        default=None,
        null=True,
        blank=True,
        help_text='If left blank sys will only ping')
    frequency_in_minutes = models.FloatField(default=30)
    status_code = models.IntegerField(default=200)
    severity_level = models.IntegerField(default=0)
    status_text = models.CharField(max_length=255,
                                   default=None,
                                   null=True,
                                   blank=True,
                                   editable=False)
    special_status_text = models.CharField(
        max_length=255,
        default=None,
        null=True,
        blank=True,
        help_text='Add a message for people to see when is down')
    response_text = models.TextField(default=None, null=True, blank=True)
    last_check = models.DateTimeField(default=None, null=True, blank=True)

    status = models.CharField(max_length=20,
                              choices=STATUS,
                              default=OPERATIONAL)

    application = models.ForeignKey(Application, on_delete=models.CASCADE)

    paused_until = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        help_text='if you want to stop checking for a period of time')

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.url


class MonitorScript(models.Model):

    script_slug = models.SlugField(default=None, null=True, blank=True)
    script_body = models.TextField(default=None, null=True, blank=True)

    frequency_delta = models.DurationField(
        default=timedelta(minutes=30),
        help_text=
        'How long to wait for the next execution, defaults to 30 minutes')
    status_code = models.IntegerField(default=200)
    severity_level = models.IntegerField(default=0)
    status_text = models.CharField(max_length=255,
                                   default=None,
                                   null=True,
                                   blank=True,
                                   editable=False)
    special_status_text = models.CharField(
        max_length=255,
        default=None,
        null=True,
        blank=True,
        help_text='Add a message for people to see when is down')
    response_text = models.TextField(default=None, null=True, blank=True)
    last_run = models.DateTimeField(default=None, null=True, blank=True)

    status = models.CharField(max_length=20,
                              choices=STATUS,
                              default=OPERATIONAL)

    application = models.ForeignKey(Application, on_delete=models.CASCADE)

    paused_until = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        help_text='if you want to stop checking for a period of time')

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        slug = 'unknow' if not self.script_slug else self.script_slug
        return f'{slug}({self.id})'
