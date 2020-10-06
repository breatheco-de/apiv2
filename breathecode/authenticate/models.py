from django.contrib.auth.models import User, Group
from django.conf import settings
from django.db import models
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
import rest_framework.authtoken.models
from django.utils import timezone

class UserAutentication(User):
    class Meta:
        proxy = True

class Profile(models.Model):
    user   = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar_url = models.CharField(max_length=255, blank=True, null=True, default=None)
    bio = models.CharField(max_length=255, blank=True, null=True)
    twitter_username = models.CharField(max_length=50, blank=True, null=True)
    blog = models.CharField(max_length=150, blank=True, null=True)

class CredentialsGithub(models.Model):
    github_id = models.IntegerField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True)
    
    token = models.CharField(max_length=255)
    email = models.CharField(blank=False, unique=True, max_length=150)
    avatar_url = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=150, blank=True, null=True)
    blog = models.CharField(max_length=150, blank=True, null=True)
    bio = models.CharField(max_length=255, blank=True, null=True)
    company = models.CharField(max_length=150, blank=True, null=True)
    twitter_username = models.CharField(max_length=50, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.email} ({self.user.id})"

class CredentialsQuickBooks(models.Model):
    quibooks_code = models.CharField(max_length=255, primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True)
    quibooks_realmid = models.CharField(max_length=255)
    
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

class Token(rest_framework.authtoken.models.Token):
    '''
    create multi token per user - override default rest_framework Token class
    replace model one-to-one relationship with foreign key
    '''
    key = models.CharField(max_length=40, db_index=True, unique=True)
    #Foreign key relationship to user for many-to-one relationship
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='auth_token',
        on_delete=models.CASCADE, verbose_name=_("User")
    )
    token_type = models.CharField(max_length=64, default='temporal')
    expires_at = models.DateTimeField(default=None, blank=True, null=True)

    def save(self, *args, **kwargs):
        # by default token expires one day after
        if self.expires_at == None:
            utc_now = timezone.now()
            if self.token_type == 'login':
                self.expires_at = utc_now + timezone.timedelta(days=1)
            else:
                self.expires_at = utc_now + timezone.timedelta(minutes=10)
        super().save(*args, **kwargs)

    def create_temp(user):
        token, created = Token.objects.get_or_create(user=user, token_type="temporal")
        return token

    def get_valid(token, token_type="temporal"):
        utc_now = timezone.now()
        # delete expired tokens
        Token.objects.filter(expires_at__lt=utc_now).delete()
        # find among any non-expired token
        _token = Token.objects.filter(key=token, expires_at__gt=utc_now).first()
        if _token is None:
            return None

        return _token
 
    class Meta:
        # ensure user and name are unique
        unique_together = (('user', 'key'),)