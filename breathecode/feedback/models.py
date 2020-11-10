from django.db import models
from django.contrib.auth.models import User
from breathecode.admissions.models import Academy, Cohort
from breathecode.events.models import Event

class UserProxy(User):
    class Meta:
        proxy = True
class CohortProxy(Cohort):
    class Meta:
        proxy = True

PENDING = 'PENDING'
SENT = 'SENT'
ANSWERED = 'ANSWERED'
OPENED = 'OPENED'
EXPIRED = 'EXPIRED'
SURVEY_STATUS = (
    (PENDING, 'Pending'),
    (SENT, 'Sent'),
    (OPENED, 'Opened'),
    (EXPIRED, 'Expired'),
)
class Answer(models.Model):
    title = models.CharField(max_length=200, blank=True)
    lowest = models.CharField(max_length=50, default='not likely')
    highest = models.CharField(max_length=50, default='very likely')
    lang = models.CharField(max_length=3, blank=True, default='en')

    cohort = models.ForeignKey(Cohort, on_delete=models.SET_NULL, default=None, blank=True, null=True)
    academy = models.ForeignKey(Academy, on_delete=models.SET_NULL, default=None, blank=True, null=True)
    mentor = models.ForeignKey(User, related_name='mentor_set', on_delete=models.SET_NULL, default=None, blank=True, null=True)
    event = models.ForeignKey(Event, on_delete=models.SET_NULL, default=None, blank=True, null=True)
    
    score = models.CharField(max_length=250, default=None, blank=True, null=True)
    comment = models.CharField(max_length=255, default=None, blank=True, null=True)

    status = models.CharField(max_length=15, choices=SURVEY_STATUS, default=PENDING)

    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None, blank=True, null=True)

    opened_at = models.DateTimeField(default=None, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

# class SurveyLog(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE, default=None, blank=True, null=True)

#     status = models.CharField(max_length=1, choices=SURVEY_STATUS, default=PENDING)
#     answer = models.ForeignKey(Answer, on_delete=models.CASCADE, null=True, default=None)

#     created_at = models.DateTimeField(auto_now_add=True, editable=False)
#     updated_at = models.DateTimeField(auto_now=True, editable=False)