from django.contrib.auth.models import User, Group
from django.db import models
from rest_framework import serializers


class CredentialsGithub(models.Model):
    github_id = models.IntegerField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True)
    
    token = models.CharField(max_length=255)
    email = models.CharField(blank=False, unique=True, max_length=150)
    avatar_url = models.CharField(max_length=255)
    name = models.CharField(max_length=150)
    blog = models.CharField(max_length=150)
    bio = models.CharField(max_length=255)
    company = models.CharField(max_length=150)
    twitter_username = models.CharField(max_length=50, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
