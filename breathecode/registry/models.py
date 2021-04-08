from django.db import models
from django.contrib.auth.models import User
from breathecode.admissions.models import Academy, Cohort
from breathecode.events.models import Event

PUBLIC='PUBLIC'
UNLISTED='UNLISTED'
PRIVATE='PRIVATE'
VISIBILITY = (
    (PUBLIC, 'Public'),
    (UNLISTED, 'Unlisted'),
    (PRIVATE, 'Private'),
)

PROJECT='PROJECT'
EXERCISE='EXERCISE'
LESSON='LESSON'
VIDEO='VIDEO'
TYPE = (
    (PROJECT, 'Project'),
    (EXERCISE, 'Exercise'),
    (LESSON, 'Lesson'),
    (LESSON, 'Video'),
)


OK='OK'
WARNING='WARNING'
ERROR='ERROR'
ASSET_STATUS = (
    (OK, 'Ok'),
    (WARNING, 'Warning'),
    (ERROR, 'Error'),
)
class Asset(models.Model):
    slug = models.SlugField(max_length=200, primary_key=True)
    title = models.CharField(max_length=200, blank=True)
    lang = models.CharField(max_length=3, blank=True, default='en')
    
    url = models.URLField()
    preview = models.URLField()
    description = models.TextField()

    interactive = models.BooleanField(default=False)
    with_solutions = models.BooleanField(default=False)
    with_video = models.BooleanField(default=False)
    gitpod = models.BooleanField(default=False)
    duration = models.IntegerField()

    visibility = models.CharField(max_length=20, choices=VISIBILITY, default=PUBLIC)
    asset_type = models.CharField(max_length=20, choices=TYPE)

    status = models.CharField(max_length=20, choices=ASSET_STATUS, default=OK)
    status_text = models.TextField(null=True, default=None, blank=True)

    author = models.ForeignKey(User, on_delete=models.SET_NULL, default=None, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
