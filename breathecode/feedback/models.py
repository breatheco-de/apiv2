from django.db import models
from django.contrib.auth.models import User
from breathecode.admissions.models import Academy, Cohort
from breathecode.events.models import Event

class UserProxy(User):
    class Meta:
        proxy = True

class Answer(models.Model):
    title = models.CharField(max_length=200, blank=True)

    cohort = models.ForeignKey(Cohort, on_delete=models.SET_NULL, default=None, blank=True, null=True)
    academy = models.ForeignKey(Academy, on_delete=models.SET_NULL, default=None, blank=True, null=True)
    mentor = models.ForeignKey(User, related_name='mentor_set', on_delete=models.SET_NULL, default=None, blank=True, null=True)
    event = models.ForeignKey(Event, on_delete=models.SET_NULL, default=None, blank=True, null=True)
    
    score = models.CharField(max_length=250, blank=True)
    comment = models.CharField(max_length=255, blank=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


class SurveyLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None, blank=True, null=True)

    answered_at = models.DateTimeField(null=True, default=None, blank=True)
    token = models.CharField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)