import re
from breathecode.admissions.models import Academy
from breathecode.authenticate.models import ProfileAcademy
from django.contrib.auth.models import User
from django.db import models
from slugify import slugify


class MentorshipService(models.Model):
    slug = models.SlugField(max_length=150, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(max_length=450)

    price_per_hour = models.FloatField()
    
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.name} ({self.id})'

class MentorAvailableTimeSlot(TimeSlot):
    
    mentor = models.ForeignKey(ProfileAcademy, on_delete=models.CASCADE)
    service = models.ForeignKey(MentorshipService, on_delete=models.CASCADE, blank=True, null=True, default=None, help_text="The availability can be constrained to one particular service (or not)")

# class MentorshipSession(models.Model):
#     slug = models.SlugField(max_length=150, unique=True)
#     name = models.CharField(max_length=150)

#     created_at = models.DateTimeField(auto_now_add=True, editable=False)
#     updated_at = models.DateTimeField(auto_now=True, editable=False)

#     def __str__(self):
#         return f'{self.name} ({self.id})'
