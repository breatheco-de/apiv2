# from breathecode.admissions.models import Academy
from django.db import models

# Create your models here.


class Platform(models.Model):
    """ Create a new platform for Jobs"""
    name = models.CharField(max_length=150)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.name} ({self.id})'


SYNCHED = 'SYNCHED'
PENDING = 'PENDING'
WARNING = 'WARNING'
ERROR = 'ERROR'
SPIDER_STATUS = (
    (SYNCHED, 'Synched'),
    (PENDING, 'Pending'),
    (WARNING, 'Warning'),
    (ERROR, 'Error'),
)


class Spider(models.Model):
    """ Create a new platform for Jobs"""
    name = models.CharField(max_length=150)
    zyte_spider_number = models.IntegerField()
    zyte_job_number = models.IntegerField()
    status = models.CharField(max_length=15, choices=SPIDER_STATUS, default=PENDING)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.name} ({self.id})'


class Job(models.Model):
    """ Create a new platform for Jobs"""
    name = models.CharField(max_length=150)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.name} ({self.id})'


# Create your models here.
#This is a mommit
