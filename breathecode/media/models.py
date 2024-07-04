from breathecode.admissions.models import Academy
from django.db import models

__all__ = ["Category", "Media", "MediaResolution"]


class Category(models.Model):
    slug = models.SlugField(max_length=150, unique=True)
    name = models.CharField(max_length=150)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.name} ({self.id})"


class Media(models.Model):
    slug = models.SlugField(max_length=150, unique=True)
    name = models.CharField(max_length=150)
    mime = models.CharField(max_length=60)
    url = models.URLField(max_length=255)
    thumbnail = models.URLField(max_length=255, blank=True, null=True)
    hash = models.CharField(max_length=64)
    hits = models.IntegerField(default=0)

    categories = models.ManyToManyField(Category, blank=True)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.name} ({self.id} - {self.slug})"


class MediaResolution(models.Model):
    hash = models.CharField(max_length=64)
    width = models.IntegerField()
    height = models.IntegerField()
    hits = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.hash} ({self.width}x{self.height})"
