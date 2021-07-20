import re
from breathecode.admissions.models import Academy
from django.contrib.auth.models import User
from django.db import models
from slugify import slugify


# class MentorProfile(models.Model):
#     slug = models.SlugField(max_length=150, unique=True)
#     name = models.CharField(max_length=150)

#     created_at = models.DateTimeField(auto_now_add=True, editable=False)
#     updated_at = models.DateTimeField(auto_now=True, editable=False)

#     def __str__(self):
#         return f'{self.name} ({self.id})'

# class MentorshipSession(models.Model):
#     slug = models.SlugField(max_length=150, unique=True)
#     name = models.CharField(max_length=150)

#     created_at = models.DateTimeField(auto_now_add=True, editable=False)
#     updated_at = models.DateTimeField(auto_now=True, editable=False)

#     def __str__(self):
#         return f'{self.name} ({self.id})'
