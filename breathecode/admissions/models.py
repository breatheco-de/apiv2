import os
from django.contrib.auth.models import User
from django.db import models
from .actions import remove_bucket_object, get_bucket_object
from pprint import pprint

def get_user_label(self):
    return f"{self.first_name} {self.last_name} ({self.email})"
User.add_to_class("__str__", get_user_label)
class UserAdmissions(User):
    class Meta:
        proxy = True

class Country(models.Model):
    code = models.CharField(max_length=3, primary_key=True)
    name = models.CharField(max_length=30)

    def __str__(self):
        return f"{self.name} ({self.code})"

class City(models.Model):
    name = models.CharField(max_length=30)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

INACTIVE = 'INACTIVE'
ACTIVE = 'ACTIVE'
DELETED = 'DELETED'
ACADEMY_STATUS = (
    (INACTIVE, 'Inactive'),
    (ACTIVE, 'Active'),
    (DELETED, 'Deleted'),
)
class Academy(models.Model):
    slug = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=150)
    logo_url = models.CharField(max_length=255)
    website_url = models.CharField(max_length=255, blank=True, null=True, default=None)

    street_address = models.CharField(max_length=250)
    city = models.ForeignKey(City, models.SET_NULL, blank=True, null=True)
    country = models.ForeignKey(Country, models.SET_NULL, blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    zip_code = models.IntegerField(blank=True, null=True)
 
    active_campaign_slug = models.SlugField(max_length=100, unique=False, null=True, default=None)

    status = models.CharField(max_length=15, choices=ACADEMY_STATUS, default=ACTIVE)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    logistical_information = models.CharField(max_length=150,  blank=True, null=True)

    def default_ac_slug(self):
        return self.slug

    def __str__(self):
        return self.name

    # def delete(self, *args, **kwargs):
    #     remove_bucket_object("location-"+self.slug)
    #     super(Image, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        if os.environ.get('ENV') != 'development':
            obj = get_bucket_object(f'location-{self.slug}')
            if obj is not None:
                self.logo_url = obj.public_url

        super().save(*args, **kwargs)  # Call the "real" save() method.

PARTIME = 'PART-TIME'
FULLTIME = 'FULL-TIME'
SCHEDULE_TYPE = (
    (PARTIME, 'Part-Time'),
    (FULLTIME, 'Full-Time'),
)
class Certificate(models.Model):
    slug = models.SlugField(max_length=100)
    name = models.CharField(max_length=150)

    logo = models.CharField(max_length=250, blank=True, null=True, default=None)
    duration_in_hours = models.IntegerField()
    duration_in_days = models.IntegerField()
    week_hours = models.IntegerField(null=True, default=None)

    schedule_type = models.CharField(max_length=15, choices=SCHEDULE_TYPE, default='PART-TIME')

    description = models.TextField(max_length=450)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name

    # def delete(self, *args, **kwargs):
    #     remove_bucket_object("certificate-logo-"+self.slug)
    #     super(Image, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):

        obj = get_bucket_object("certificate-logo-"+self.slug)
        if obj is not None:
            self.logo = obj.public_url
        pprint(obj)
        print('yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy', obj)
        print('yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy', obj.public_url)
        print('yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy', *args)
        print('yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy', **kwargs)
        print('yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy', super().save)

        super().save(*args, **kwargs)  # Call the "real" save() method.


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
    ending_date = models.DateTimeField(blank=True, null=True)
    current_day = models.IntegerField()
    stage = models.CharField(max_length=15, choices=COHORT_STAGE, default=INACTIVE)

    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    certificate = models.ForeignKey(Certificate, on_delete=models.CASCADE)

    language = models.CharField(max_length=2, default='en')

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
SUSPENDED = 'SUSPENDED'
GRADUATED = 'GRADUATED'
DROPPED = 'DROPPED'
EDU_STATUS = (
    (ACTIVE, 'Active'),
    (POSTPONED, 'Postponed'),
    (GRADUATED, 'Graduated'),
    (SUSPENDED, 'Suspended'),
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