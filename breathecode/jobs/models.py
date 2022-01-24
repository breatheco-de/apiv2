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


class Position(models.Model):
    """ something """
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.name} ({self.id})'


class ZyteProject(models.Model):
    """ Create a new platform for Jobs"""
    zyte_api_key = models.CharField(max_length=150)
    zyte_api_deploy = models.CharField(max_length=50)

    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.platform} {self.zyte_api_key} {self.zyte_api_deploy} ({self.id})'


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
    position = models.ForeignKey(Position, on_delete=models.CASCADE, null=False, blank=False)
    job = models.CharField(max_length=150)
    loc = models.CharField(max_length=150)
    zyte_project = models.ForeignKey(ZyteProject, on_delete=models.CASCADE, null=False, blank=False)
    zyte_spider_number = models.IntegerField(help_text='This number must be copy from ZYTE')
    zyte_job_number = models.IntegerField(help_text='Start at 0 but increase on each fetch')
    zyte_fetch_count = models.IntegerField(help_text='The number of spider job excecutions to fetch')
    zyte_last_fetch_date = models.DateField(null=True)
    status = models.CharField(max_length=15, choices=SPIDER_STATUS, default=PENDING)
    sync_status = models.CharField(max_length=15, choices=SPIDER_STATUS, default=PENDING)
    sync_desc = models.CharField(max_length=200, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.name} ({self.id})'


class PositionAlias(models.Model):
    """ something """
    name = models.CharField(max_length=100)
    position = models.ForeignKey(Position, on_delete=models.CASCADE, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.name} ({self.id})'


class Tag(models.Model):
    """ something """
    slug = models.SlugField(max_length=200, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.slug} ({self.id})'


class Location(models.Model):
    """ something """
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.name} ({self.id})'


class LocationAlias(models.Model):
    """ something """
    name = models.CharField(max_length=100)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.name} ({self.id})'


class Employer(models.Model):
    """ something """
    name = models.CharField(max_length=100)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.name} {self.name} ({self.id})'


OPENED = 'OPENED'
FILLED = 'FILLED'
JOB_STATUS = (
    (OPENED, 'Opened'),
    (FILLED, 'Filled'),
)

FULLTIME = 'Full-time'
INTERNSHIP = 'Internship'
PARTTIME = 'Part-time'
TEMPORARY = 'Temporary'
CONTRACT = 'Contract'
JOB_TYPE = (
    (FULLTIME, 'Full-time'),
    (INTERNSHIP, 'Internship'),
    (PARTTIME, 'Part-time'),
    (TEMPORARY, 'Temporary'),
    (CONTRACT, 'Contract'),
)


class Job(models.Model):
    """ Create a new platform for Jobs"""
    title = models.CharField(max_length=150)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, null=False, blank=False)
    published_date_raw = models.CharField(max_length=50)
    published_date_processed = models.DateField(null=True)
    status = models.CharField(max_length=15, choices=JOB_STATUS, default=OPENED)
    apply_url = models.URLField(max_length=500)
    min_salary = models.FloatField(null=True, blank=True)
    max_salary = models.FloatField(null=True, blank=True)
    salary = models.CharField(max_length=253, null=True, blank=True)
    job_type = models.CharField(max_length=15, choices=JOB_TYPE, default=FULLTIME)
    remote = models.BooleanField(default=False, verbose_name='Remote')
    employer = models.ForeignKey(Employer, on_delete=models.CASCADE, null=True, blank=True)
    position = models.ForeignKey(Position, on_delete=models.CASCADE, null=False, blank=False)
    tags = models.ManyToManyField(Tag)
    locations = models.ManyToManyField(Location)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.title} ({self.id})'
