from django.contrib.auth.models import User
from django.db import models

class Academy(models.Model):
    slug = models.CharField(max_length=150, unique=True)
    name = models.CharField(max_length=150)

    street_address = models.CharField(max_length=250)
    country = models.CharField(max_length=30)
    city = models.CharField(max_length=30)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    state = models.CharField(max_length=30)
    zip_code = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    logistical_information = models.CharField(max_length=150)

    def __str__(self):
        return self.name

class Certificate(models.Model):
    slug = models.CharField(max_length=150)
    name = models.CharField(max_length=150)

    logo = models.CharField(max_length=250, blank=True)
    duration_in_hours = models.IntegerField()
    duration_in_days = models.IntegerField()
    week_hours = models.IntegerField()

    description = models.TextField(max_length=450)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name

class AcademyCertificate(models.Model):
    certificate = models.ForeignKey(Certificate, on_delete=models.CASCADE)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


INACTIVE = 'INACTIVE'
PREWORK = 'PREWORK'
STARTED = 'STARTED'
FINAL_PROJECT = 'FINAL_PROJECT'
ENDED = 'ENDED'
DELETED = 'DELETED'
COHORT_STAGE = (
    (INACTIVE, 'Inactive'),
    (PREWORK, 'Prework'),
    (STARTED, 'Started'),
    (FINAL_PROJECT, 'Final Project'),
    (ENDED, 'Ended'),
    (DELETED, 'Deleted'),
)
class Cohort(models.Model):
    slug = models.CharField(max_length=150, unique=True)
    name = models.CharField(max_length=150)

    kickoff_date = models.DateTimeField()
    ending_date = models.DateTimeField()
    current_day = models.IntegerField()
    stage = models.CharField(max_length=15, choices=COHORT_STAGE, default=INACTIVE)
    
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    certificate = models.ForeignKey(Certificate, on_delete=models.CASCADE)

    language = models.CharField(max_length=2, default='en')

    online_room_url = models.CharField(max_length=250, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name

TEACHER = 'TEACHER'
ASSISTANT = 'ASSISTANT'
STUDENT = 'STUDENT'
COHORT_ROLE = (
    (TEACHER, 'Teacher'),
    (ASSISTANT, 'Assistant'),
    (STUDENT, 'Student'),
)

FULLY_PAID = 'FULLY_PAID'
UP_TO_DATE = 'UP_TO_DATE'
LATE = 'LATE'
FINANTIAL_STATUS = (
    (FULLY_PAID, 'Fully Paid'),
    (UP_TO_DATE, 'Up to date'),
    (LATE, 'Late'),
)

ACTIVE = 'ACTIVE'
POSTPONED = 'POSTPONED'
GRADUATED = 'GRADUATED'
DROPPED = 'DROPPED'
EDU_STATUS = (
    (ACTIVE, 'Active'),
    (POSTPONED, 'Postponed'),
    (GRADUATED, 'Graduated'),
    (DROPPED, 'Dropped'),
)
class CohortUser(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE)
    role = models.CharField(max_length=9, choices=COHORT_ROLE, default=STUDENT)

    finantial_status = models.CharField(max_length=15, choices=FINANTIAL_STATUS, default=None, null=True)
    educational_status = models.CharField(max_length=15, choices=EDU_STATUS, default=None, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)