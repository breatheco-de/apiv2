from datetime import datetime
from typing import Any
from django.contrib.auth.models import User, Group, Permission
from django.core.exceptions import MultipleObjectsReturned
from django.conf import settings
from django.db.models import Q
from django.db import models
from django.utils.translation import ugettext_lazy as _
import rest_framework.authtoken.models
from django.utils import timezone
from django.core.validators import RegexValidator
from django.contrib.contenttypes.models import ContentType

from breathecode.authenticate.exceptions import (BadArguments, InvalidTokenType, TokenNotFound,
                                                 TryToGetOrCreateAOneTimeToken)
from breathecode.utils.validators import validate_language_code
from .signals import invite_accepted, profile_academy_saved
from breathecode.admissions.models import Academy, Cohort

__all__ = [
    'User', 'Group', 'ContentType', 'Permission', 'UserProxy', 'Profile', 'Capability', 'Role', 'UserInvite',
    'ProfileAcademy', 'CredentialsGithub', 'CredentialsSlack', 'CredentialsFacebook', 'CredentialsQuickBooks',
    'CredentialsGoogle', 'DeviceId', 'Token'
]

TOKEN_TYPE = ['login', 'one_time', 'temporal', 'permanent']
LOGIN_TOKEN_LIFETIME = timezone.timedelta(days=1)
TEMPORAL_TOKEN_LIFETIME = timezone.timedelta(minutes=10)


class UserProxy(User):

    class Meta:
        proxy = True


class AcademyProxy(Academy):

    class Meta:
        proxy = True


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar_url = models.CharField(max_length=255, blank=True, null=True, default=None)
    bio = models.CharField(max_length=255, blank=True, null=True)

    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    phone = models.CharField(validators=[phone_regex], max_length=17, blank=True,
                             default='')  # validators should be a list

    show_tutorial = models.BooleanField(
        default=True, help_text='Set true if you want to show the tutorial on the user UI/UX')

    twitter_username = models.CharField(max_length=50, blank=True, null=True)
    github_username = models.CharField(max_length=50, blank=True, null=True)
    portfolio_url = models.CharField(max_length=50, blank=True, null=True)
    linkedin_url = models.CharField(max_length=50, blank=True, null=True)

    blog = models.CharField(max_length=150, blank=True, null=True)


class UserSetting(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    lang = models.CharField(max_length=5, default='en', validators=[validate_language_code])
    main_currency = models.ForeignKey('payments.Currency', on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Capability(models.Model):
    slug = models.SlugField(max_length=40, primary_key=True)
    description = models.CharField(max_length=255, blank=True, null=True, default=None)

    def __str__(self):
        return f'{self.slug}'


class Role(models.Model):
    slug = models.SlugField(max_length=25, primary_key=True)
    name = models.CharField(max_length=255, blank=True, null=True, default=None)
    capabilities = models.ManyToManyField(Capability)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.name} ({self.slug})'


PENDING = 'PENDING'
ACCEPTED = 'ACCEPTED'
REJECTED = 'REJECTED'
WAITING_LIST = 'WAITING_LIST'
INVITE_STATUS = (
    (PENDING, 'Pending'),
    (REJECTED, 'Rejected'),
    (ACCEPTED, 'Accepted'),
    (WAITING_LIST, 'Waiting list'),
)

PENDING = 'PENDING'
DONE = 'DONE'
ERROR = 'ERROR'
PROCESS_STATUS = (
    (PENDING, 'Pending'),
    (DONE, 'Done'),
    (ERROR, 'Error'),
)


class UserInvite(models.Model):

    email = models.CharField(blank=False, max_length=150, null=True, default=None)

    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, null=True, default=None, blank=True)
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, null=True, default=None, blank=True)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, default=None, blank=True)

    first_name = models.CharField(max_length=100, default=None, null=True)
    last_name = models.CharField(max_length=100, default=None, null=True)

    token = models.CharField(max_length=255, unique=True)

    author = models.ForeignKey(User, on_delete=models.CASCADE, null=True, default=None)

    status = models.CharField(max_length=15, choices=INVITE_STATUS, default=PENDING)

    process_status = models.CharField(max_length=7, choices=PROCESS_STATUS, default=PENDING)
    process_message = models.CharField(max_length=150, default='')

    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    phone = models.CharField(validators=[phone_regex], max_length=17, blank=True,
                             default='')  # validators should be a list

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    sent_at = models.DateTimeField(default=None, null=True, blank=True)

    def __str__(self):
        return f'Invite for {self.email}'


INVITED = 'INVITED'
ACTIVE = 'ACTIVE'
PROFILE_ACADEMY_STATUS = (
    (INVITED, 'Invited'),
    (ACTIVE, 'Active'),
)


class ProfileAcademy(models.Model):

    def __init__(self, *args, **kwargs):
        super(ProfileAcademy, self).__init__(*args, **kwargs)
        self.__old_status = self.status

    user = models.ForeignKey(User, on_delete=models.SET_NULL, default=None, null=True)

    email = models.CharField(blank=False, max_length=150, null=True, default=None)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    first_name = models.CharField(max_length=100, default=None, null=True)
    last_name = models.CharField(max_length=100, default=None, null=True)
    address = models.CharField(max_length=255, blank=True, default=None, null=True)

    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    phone = models.CharField(validators=[phone_regex], max_length=17, blank=True,
                             default='')  # validators should be a list

    status = models.CharField(max_length=15, choices=PROFILE_ACADEMY_STATUS, default=INVITED)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.email} for academy ({self.academy.name})'

    def save(self, *args, **kwargs):

        if self.__old_status != self.status and self.status == 'ACTIVE':
            invite_accepted.send(instance=self, sender=ProfileAcademy)

        super().save(*args, **kwargs)  # Call the "real" save() method.


class CredentialsGithub(models.Model):
    github_id = models.IntegerField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True)

    token = models.CharField(max_length=255)
    email = models.CharField(blank=False, unique=True, max_length=150)
    avatar_url = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=150, blank=True, null=True)
    username = models.CharField(max_length=35, blank=True, null=True)
    blog = models.CharField(max_length=150, blank=True, null=True)
    bio = models.CharField(max_length=255, blank=True, null=True)
    company = models.CharField(max_length=150, blank=True, null=True)
    twitter_username = models.CharField(max_length=50, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.email} ({self.user.id})'

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()

        return super().save(*args, **kwargs)


class CredentialsSlack(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True)

    token = models.CharField(max_length=255)
    bot_user_id = models.CharField(max_length=50)
    app_id = models.CharField(max_length=50)

    authed_user = models.CharField(max_length=50)

    team_id = models.CharField(max_length=50)
    team_name = models.CharField(max_length=100)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.user.email} ({self.authed_user})'


class CredentialsFacebook(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    academy = models.OneToOneField(Academy, on_delete=models.CASCADE, blank=True)

    token = models.CharField(max_length=255)
    expires_at = models.DateTimeField()
    facebook_id = models.BigIntegerField(null=True, default=None)
    email = models.CharField(blank=False, null=True, default=None, max_length=150)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'Team {str(self.user)}'


class CredentialsQuickBooks(models.Model):
    quibooks_code = models.CharField(max_length=255, primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True)
    quibooks_realmid = models.CharField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


class CredentialsGoogle(models.Model):

    token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255)
    expires_at = models.DateTimeField()

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


class Token(rest_framework.authtoken.models.Token):
    '''
    create multi token per user - override default rest_framework Token class
    replace model one-to-one relationship with foreign key
    '''
    key = models.CharField(max_length=40, db_index=True, unique=True)
    #Foreign key relationship to user for many-to-one relationship
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             related_name='auth_token',
                             on_delete=models.CASCADE,
                             verbose_name=_('User'))
    token_type = models.CharField(max_length=64, default='temporal')
    expires_at = models.DateTimeField(default=None, blank=True, null=True)

    def save(self, *args, **kwargs):
        without_expire_at = not self.expires_at
        if without_expire_at and self.token_type == 'login':
            utc_now = timezone.now()
            self.expires_at = utc_now + LOGIN_TOKEN_LIFETIME

        if without_expire_at and self.token_type == 'temporal':
            utc_now = timezone.now()
            self.expires_at = utc_now + TEMPORAL_TOKEN_LIFETIME

        if self.token_type == 'one_time' or self.token_type == 'permanent':
            self.expires_at = None

        super().save(*args, **kwargs)

    @staticmethod
    def delete_expired_tokens(utc_now: datetime = timezone.now()) -> None:
        """Delete expired tokens"""
        utc_now = timezone.now()
        Token.objects.filter(expires_at__lt=utc_now).delete()

    @classmethod
    def get_or_create(cls, user, token_type: str, **kwargs: Any):
        utc_now = timezone.now()
        kwargs['token_type'] = token_type

        cls.delete_expired_tokens(utc_now)

        if token_type not in TOKEN_TYPE:
            raise InvalidTokenType(f'Invalid token_type, correct values are {", ".join(TOKEN_TYPE)}')

        has_hours_length = 'hours_length' in kwargs
        has_expires_at = 'expires_at' in kwargs

        if (token_type == 'one_time' or token_type == 'permanent') and (has_hours_length or has_expires_at):
            raise BadArguments(f'You can\'t provide token_type=\'{token_type}\' and '
                               'has_hours_length or has_expires_at together')

        if has_hours_length and has_expires_at:
            raise BadArguments('You can\'t provide hours_length and expires_at argument together')

        if has_hours_length:
            kwargs['expires_at'] = utc_now + timezone.timedelta(hours=kwargs['hours_length'])
            del kwargs['hours_length']

        token = None
        created = False

        try:
            if token_type == 'one_time':
                raise TryToGetOrCreateAOneTimeToken()

            token, created = Token.objects.get_or_create(user=user, **kwargs)

        except MultipleObjectsReturned:
            token = Token.objects.filter(user=user, **kwargs).first()

        except TryToGetOrCreateAOneTimeToken:
            created = True
            token = Token.objects.create(user=user, **kwargs)

        return token, created

    @classmethod
    def get_valid(cls, token: str):
        utc_now = timezone.now()
        cls.delete_expired_tokens(utc_now)

        # find among any non-expired token
        return Token.objects.filter(key=token).filter(Q(expires_at__gt=utc_now)
                                                      | Q(expires_at__isnull=True)).first()

    @classmethod
    def validate_and_destroy(cls, hash: str) -> User:
        token = Token.objects.filter(key=hash, token_type='one_time').first()
        if not token:
            raise TokenNotFound()

        user = token.user
        token.delete()

        return user

    class Meta:
        # ensure user and name are unique
        unique_together = (('user', 'key'), )


class DeviceId(models.Model):
    name = models.CharField(max_length=40)
    key = models.CharField(max_length=64)


class GitpodUser(models.Model):

    github_username = models.CharField(max_length=40)
    assignee_id = models.CharField(max_length=64)
    position_in_gitpod_team = models.PositiveSmallIntegerField()
    delete_status = models.TextField(null=True, default=None, blank=True)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, default=None, blank=True)
    academy = models.ForeignKey(Academy, on_delete=models.SET_NULL, null=True, default=None, blank=True)
    target_cohort = models.ForeignKey(Cohort, on_delete=models.SET_NULL, null=True, default=None, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    expires_at = models.DateTimeField(
        default=None,
        null=True,
        blank=True,
        help_text=
        'If a gitpod user is not connected to a real user and academy in the database, it will be deleted ASAP'
    )
