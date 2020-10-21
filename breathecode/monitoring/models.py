from django.db import models
from django.contrib.auth.models import User
from breathecode.admissions.models import Academy
OPERATIONAL='OPERATIONAL'
MINOR='MINOR'
CRITICAL='CRITICAL'
STATUS = (
    (OPERATIONAL, 'Operational'),
    (MINOR, 'Minor'),
    (CRITICAL, 'Critical'),
)
class Application(models.Model):
    title = models.CharField(max_length=100)

    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    status_text = models.CharField(max_length=255, default=None, null=True, blank=True)
    notify_email = models.CharField(max_length=255, default=None, null=True)

    status = models.CharField(max_length=20, choices=STATUS, default=OPERATIONAL)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.title

class Endpoint(models.Model):

    url = models.CharField(max_length=255)
    test_pattern = models.CharField(max_length=100, default=None, null=True, blank=True, help_text='If left blank sys will only ping')
    frequency_in_minutes = models.FloatField(default=30)
    status_code = models.FloatField(default=200)
    severity_level = models.IntegerField(default=0)
    status_text = models.CharField(max_length=255, default=None, null=True, blank=True)
    response_text = models.TextField(default=None, null=True, blank=True)
    last_check = models.DateTimeField(default=None, null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS, default=OPERATIONAL)

    application = models.ForeignKey(Application, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.url