from django.db import models
from django.contrib.postgres.fields import JSONField

# Create your models here.
class Course(models.Model):
    slug = models.SlugField(max_length=150, unique=True)
    name = models.CharField(max_length=150)

    logo = models.CharField(max_length=250, blank=True, null=True, default=None)
    duration_in_hours = models.IntegerField()
    duration_in_days = models.IntegerField()
    week_hours = models.IntegerField(null=True, default=None)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name

class Syllabus(models.Model):

    version = models.PositiveSmallIntegerField()

    json = JSONField()
    github_url = models.URLField(max_length=255, blank=True, null=True, default=None)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    @property
    def slug(self):
        return self.course.slug+".v"+str(self.version)
        

    def __str__(self):
        return self.course.name