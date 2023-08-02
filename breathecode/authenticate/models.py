from datetime import datetime
import re
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
from django import forms
from slugify import slugify

from breathecode.authenticate.exceptions import (BadArguments, InvalidTokenType, TokenNotFound,
                                                 TryToGetOrCreateAOneTimeToken)
from breathecode.utils.validators import validate_language_code
from .signals import invite_status_updated, academy_invite_accepted
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
    bio = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='User biography in user\'s language. Will be used if there are no ProfileTranslations.')

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


class ProfileTranslation(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, help_text='Profile')
    lang = models.CharField(max_length=5,
                            validators=[validate_language_code],
                            unique=True,
                            help_text='ISO 639-1 language code + ISO 3166-1 alpha-2 country code, e.g. en-US')

    bio = models.CharField(max_length=255)

    def __str__(self) -> str:
        return f'{self.lang}: {self.profile.user.email}'


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


class Scope(models.Model):
    name = models.CharField(max_length=25,
                            unique=True,
                            help_text='Descriptive and unique name that appears on the authorize UI')
    slug = models.CharField(max_length=15, unique=True, help_text='{action}:{data} for example read:repo')
    description = models.CharField(max_length=255, help_text='Description of the scope')

    def clean(self) -> None:
        if not self.slug:
            self.slug = slugify(self.name)

        if not self.description:
            raise forms.ValidationError('Scope description is required')

        if not self.slug or not re.findall(
                r'^[a-z_:]+$', self.slug) or self.slug.count(':') > 1 or self.slug.count('__') > 0:
            raise forms.ValidationError(
                'Scope slug must be in the format "action_name:data_name" or "data_name" example '
                '"read:repo" or "repo"')

        return super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} ({self.slug})'


HMAC_SHA256 = 'HMAC_SHA256'
HMAC_SHA512 = 'HMAC_SHA512'
ED25519 = 'ED25519'
AUTH_ALGORITHM = (
    (HMAC_SHA256, 'HMAC-SHA256'),
    (HMAC_SHA512, 'HMAC_SHA512'),
    (ED25519, 'ED25519'),
)

JWT = 'JWT'
SIGNATURE = 'SIGNATURE'
AUTH_STRATEGY = (
    (JWT, 'Json Web Token'),
    (SIGNATURE, 'Signature'),
)

LINK = 'LINK'
AUTH_SCHEMA = ((LINK, 'Link'), )

SYMMETRIC_ALGORITHMS = [HMAC_SHA256, HMAC_SHA512]
ASYMMETRIC_ALGORITHMS = [ED25519]


class App(models.Model):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._algorithm = self.algorithm
        self._strategy = self.strategy
        self._schema = self.schema

        self._private_key = self.private_key
        self._public_key = self.public_key

        self._webhook_url = self.webhook_url
        self._redirect_url = self.redirect_url

    name = models.CharField(max_length=25, unique=True, help_text='Descriptive and unique name of the app')
    slug = models.SlugField(
        unique=True,
        help_text='Unique slug for the app, it must be url friendly and please avoid to change it')
    description = models.CharField(max_length=255,
                                   help_text='Description of the app, it will appear on the authorize UI')

    algorithm = models.CharField(max_length=11, choices=AUTH_ALGORITHM, default=HMAC_SHA512)
    strategy = models.CharField(max_length=9, choices=AUTH_STRATEGY, default=JWT)
    schema = models.CharField(
        max_length=4,
        choices=AUTH_SCHEMA,
        default=LINK,
        help_text='Schema to use for the auth process to represent how the apps will communicate')

    required_scopes = models.ManyToManyField(Scope, blank=True, related_name='app_required_scopes')
    optional_scopes = models.ManyToManyField(Scope, blank=True, related_name='app_optional_scopes')
    agreement_version = models.IntegerField(default=1,
                                            help_text='Version of the agreement, based in the scopes')

    private_key = models.CharField(max_length=255, blank=True, null=False)
    public_key = models.CharField(max_length=255, blank=True, null=True, default=None)
    require_an_agreement = models.BooleanField(
        default=True, help_text='If true, the user will be required to accept an agreement')

    webhook_url = models.URLField()
    redirect_url = models.URLField()
    app_url = models.URLField()

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.name} ({self.slug})'

    def clean(self) -> None:
        from .actions import generate_auth_keys

        if not self.slug:
            self.slug = slugify(self.name)

        if self.public_key and self.algorithm in SYMMETRIC_ALGORITHMS:
            raise forms.ValidationError('Public key is not required for symmetric algorithms')

        if not self.public_key and not self.private_key:
            self.public_key, self.private_key = generate_auth_keys(self.algorithm)

        if self.app_url.endswith('/'):
            self.app_url = self.app_url[:-1]

        return super().clean()

    def save(self, *args, **kwargs):
        from .actions import reset_app_cache

        had_pk = self.pk

        self.full_clean()
        super().save(*args, **kwargs)

        if had_pk and (self.private_key != self._private_key or self.public_key != self._public_key
                       or self.algorithm != self._algorithm):
            key = LegacyKey()
            key.app = self

            key.algorithm = self._algorithm
            key.strategy = self._strategy
            key.schema = self._schema

            key.private_key = self._private_key
            key.public_key = self._public_key

            key.webhook_url = self._webhook_url
            key.redirect_url = self._redirect_url

            key.save()

        if had_pk:
            reset_app_cache()

        self._algorithm = self.algorithm
        self._strategy = self.strategy
        self._schema = self.schema

        self._private_key = self.private_key
        self._public_key = self.public_key

        self._webhook_url = self.webhook_url
        self._redirect_url = self.redirect_url


class OptionalScopeSet(models.Model):
    optional_scopes = models.ManyToManyField(Scope, blank=True)

    def save(self, *args, **kwargs):
        from .actions import reset_app_user_cache

        had_pk = self.pk

        self.full_clean()
        super().save(*args, **kwargs)

        self.__class__.objects.exclude(app_user_agreement__id__gte=1).exclude(id=self.id).delete()

        if had_pk:
            reset_app_user_cache()


class AppUserAgreement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    app = models.ForeignKey(App, on_delete=models.CASCADE)
    optional_scope_set = models.ForeignKey(OptionalScopeSet,
                                           on_delete=models.CASCADE,
                                           related_name='app_user_agreement')
    agreement_version = models.IntegerField(default=1, help_text='Version of the agreement that was accepted')

    def save(self, *args, **kwargs):
        from .actions import reset_app_user_cache

        had_pk = self.pk

        self.full_clean()
        super().save(*args, **kwargs)

        if had_pk:
            reset_app_user_cache()


LEGACY_KEY_LIFETIME = timezone.timedelta(minutes=2)


class LegacyKey(models.Model):

    app = models.OneToOneField(App, on_delete=models.CASCADE, related_name='legacy_key')

    algorithm = models.CharField(max_length=11, choices=AUTH_ALGORITHM)
    strategy = models.CharField(max_length=9, choices=AUTH_STRATEGY)
    schema = models.CharField(max_length=4, choices=AUTH_SCHEMA)

    private_key = models.CharField(max_length=255, blank=True, null=False)
    public_key = models.CharField(max_length=255, blank=True, null=True, default=None)

    webhook_url = models.URLField()
    redirect_url = models.URLField()

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.app.name} ({self.app.slug})'

    def clean(self) -> None:
        if self.public_key and self.algorithm in SYMMETRIC_ALGORITHMS:
            raise forms.ValidationError('Public key is not required for symmetric algorithms')

        if not self.public_key and not self.private_key:
            raise forms.ValidationError('Public and private keys are required')

        return super().clean()

    def save(self, *args, **kwargs):
        from breathecode.authenticate import tasks

        self.full_clean()
        super().save(*args, **kwargs)

        tasks.destroy_legacy_key.apply_async(args=(self.id, ), eta=timezone.now() + LEGACY_KEY_LIFETIME)

    def delete(self, *args, **kwargs):
        from . import actions
        r = super().delete(*args, **kwargs)
        actions.reset_app_cache()
        return r


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
    _old_status: str
    _email: str

    def __init__(self, *args, **kwargs):
        super(UserInvite, self).__init__(*args, **kwargs)
        self._old_status = self.status
        self._email = self.email

    email = models.CharField(blank=False, max_length=150, null=True, default=None)
    is_email_validated = models.BooleanField(default=False)

    user = models.ForeignKey(User,
                             on_delete=models.CASCADE,
                             null=True,
                             default=None,
                             blank=True,
                             related_name='invites')
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, null=True, default=None, blank=True)
    syllabus = models.ForeignKey('admissions.Syllabus',
                                 on_delete=models.CASCADE,
                                 null=True,
                                 default=None,
                                 blank=True)
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, null=True, default=None, blank=True)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, default=None, blank=True)

    first_name = models.CharField(max_length=100, default=None, null=True)
    last_name = models.CharField(max_length=100, default=None, null=True)

    token = models.CharField(max_length=255, unique=True)

    author = models.ForeignKey(User,
                               on_delete=models.CASCADE,
                               null=True,
                               default=None,
                               related_name='invites_by_author')

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

    def save(self, *args, **kwargs):

        status_updated = False
        if self.pk is None or self._old_status != self.status:
            status_updated = True

        if self.pk and self._email and self.email != self._email:
            raise forms.ValidationError('Email is readonly')

        super().save(*args, **kwargs)  # Call the "real" save() method.

        self._email = self.email

        if status_updated:
            invite_status_updated.send(instance=self, sender=UserInvite)
            self._old_status = self.status


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
            academy_invite_accepted.send(instance=self, sender=ProfileAcademy)

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


class AcademyAuthSettings(models.Model):
    academy = models.OneToOneField(Academy, on_delete=models.CASCADE)
    github_username = models.SlugField(max_length=40, blank=True)
    github_owner = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, default=None, null=True)
    github_default_team_ids = models.CharField(
        max_length=40,
        blank=True,
        default='',
        help_text='User will be invited to this github team ID when joining the github organization')
    github_is_sync = models.BooleanField(default=False,
                                         blank=False,
                                         help_text='If true, will try synching every few hours')
    github_error_log = models.JSONField(default=None,
                                        blank=True,
                                        null=True,
                                        help_text='Error trace log for github API communication')

    def add_error(self, msg):
        if self.github_error_log is None:
            self.github_error_log = []

        thirty_days_old = timezone.now() - timezone.timedelta(days=30)

        def to_datetime(date_str):
            return datetime.fromisoformat(date_str)

        self.github_error_log = [e for e in self.github_error_log if thirty_days_old < to_datetime(e['at'])]

        self.github_error_log.append({'msg': msg, 'at': str(timezone.now())})
        self.save()
        return self.github_error_log

    def clean_errors(self, msg):
        self.github_error_log = []
        self.save()
        return self.github_error_log


PENDING = 'PENDING'
SYNCHED = 'SYNCHED'
UNKNOWN = 'UNKNOWN'
PAYMENT_CONFLICT = 'PAYMENT_CONFLICT'
STORAGE_STATUS = (
    (PENDING, 'Pending'),
    (SYNCHED, 'Synched'),
    (ERROR, 'Error'),
    (UNKNOWN, 'Unknown'),
    (PAYMENT_CONFLICT, 'Payment conflict'),
)

ADD = 'ADD'
INVITE = 'INVITE'
DELETE = 'DELETE'
IGNORE = 'IGNORE'
STORAGE_ACTION = (
    (ADD, 'Add'),
    (DELETE, 'Delete'),
    (INVITE, 'Invite'),
    (IGNORE, 'Ignore'),
)


class GithubAcademyUser(models.Model):

    def __init__(self, *args, **kwargs):
        super(GithubAcademyUser, self).__init__(*args, **kwargs)
        self.__old_status = self.storage_status
        self.__old_action = self.storage_action

    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, default=None, null=True)
    username = models.SlugField(max_length=40,
                                default=None,
                                null=True,
                                blank=True,
                                help_text='Only used when the username has not been found on 4Geeks')
    storage_status = models.CharField(max_length=20, choices=STORAGE_STATUS, default=PENDING)
    storage_action = models.CharField(max_length=20, choices=STORAGE_ACTION, default=ADD)
    storage_log = models.JSONField(default=None, null=True, blank=True)
    storage_synch_at = models.DateTimeField(default=None, null=True, blank=True)
    # deletion_scheduled_at = models.DateTimeField(default=None, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        if self.user is None:
            return str(self.id) + ' ' + str(self.username)
        else:
            return str(self.user) + ' ' + str(self.username)

    @staticmethod
    def create_log(msg):
        return {'msg': msg, 'at': str(timezone.now())}

    def log(self, msg, reset=True):

        if self.storage_log is None or reset:
            self.storage_log = []

        self.storage_log.append(GithubAcademyUser.create_log(msg))

    def save(self, *args, **kwargs):
        has_mutated = False

        if self.__old_status != self.storage_status:
            has_mutated = True
        if self.__old_action != self.storage_action:
            has_mutated = True

        if not self.user and (credentials :=
                              CredentialsGithub.objects.filter(username=self.username).first()):
            self.user = credentials.user

        exit_op = super().save(*args, **kwargs)

        if has_mutated and self.storage_status == 'SYNCHED':
            prev = GithubAcademyUserLog.objects.filter(
                academy_user=self, storage_status=self.storage_status,
                storage_action=self.storage_action).order_by('-created_at').first()

            user_log = GithubAcademyUserLog(
                academy_user=self,
                storage_status=self.storage_status,
                storage_action=self.storage_action,
            )
            user_log.save()

            if prev:
                prev.valid_until = user_log.created_at
                prev.save()

        return exit_op


class GithubAcademyUserLog(models.Model):
    academy_user = models.ForeignKey(GithubAcademyUser, on_delete=models.CASCADE)
    storage_status = models.CharField(max_length=20, choices=STORAGE_STATUS, default=PENDING)
    storage_action = models.CharField(max_length=20, choices=STORAGE_ACTION, default=ADD)
    valid_until = models.DateTimeField(default=None, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


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
