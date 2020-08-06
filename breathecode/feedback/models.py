from django.db import models
from django.contrib.auth.models import User
from breathecode.admissions.models import Academy

EVENT = 'EVENT'
CERTIFICATE = 'CERTIFICATE'
WORKSHOP = 'WORKSHOP'
MENTOR = 'MENTOR'
ACADEMY = 'ACADEMY'
COHORT = 'COHORT'
ANSWER_TYPE = (
    (EVENT, 'Event'),
    (CERTIFICATE, 'Certificate'),
    (WORKSHOP, 'Workshop'),
    (MENTOR, 'Mentor'),
    (ACADEMY, 'Academy'),
    (COHORT, 'Cohort'),
)
class Answer(models.Model):
    title = models.CharField(max_length=200, blank=True)
    score = models.CharField(max_length=250, blank=True)
    comment = models.CharField(max_length=255, blank=True)

    user = models.ForeignKey(User, on_delete=models.SET_NULL, default=None, blank=True, null=True)

    entity_type = models.CharField(max_length=12, choices=ANSWER_TYPE)
    entity_id = models.PositiveIntegerField()
    entity_slug = models.SlugField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
