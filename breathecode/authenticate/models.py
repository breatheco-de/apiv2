from datetime import datetime
from typing import Tuple, TypedDict, Unpack

import rest_framework.authtoken.models
from asgiref.sync import sync_to_async
from django import forms
from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import MultipleObjectsReturned
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from breathecode.admissions.models import Academy, Cohort
from breathecode.authenticate import signals
from breathecode.authenticate.exceptions import (
    BadArguments,
    InvalidTokenType,
    TokenNotFound,
    TryToGetOrCreateAOneTimeToken,
)
from breathecode.utils.validators import validate_language_code

from .signals import academy_invite_accepted

__all__ = [
    "User",
    "Group",
    "ContentType",
    "Permission",
    "UserProxy",
    "Profile",
    "Capability",
    "Role",
    "UserInvite",
    "ProfileAcademy",
    "CredentialsGithub",
    "CredentialsSlack",
    "CredentialsFacebook",
    "CredentialsQuickBooks",
    "CredentialsGoogle",
    "DeviceId",
    "Token",
]

TOKEN_TYPE = ["login", "one_time", "temporal", "permanent"]
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
        help_text="User biography in user's language. Will be used if there are no ProfileTranslations.",
    )

    phone_regex = RegexValidator(
        regex=r"^\+?1?\d{9,15}$",
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
    )
    phone = models.CharField(
        validators=[phone_regex], max_length=17, blank=True, default=""
    )  # validators should be a list

    show_tutorial = models.BooleanField(
        default=True, help_text="Set true if you want to show the tutorial on the user UI/UX", db_index=True
    )

    twitter_username = models.CharField(max_length=64, blank=True, null=True)
    github_username = models.CharField(max_length=64, blank=True, null=True)
    portfolio_url = models.CharField(max_length=160, blank=True, null=True)
    linkedin_url = models.CharField(max_length=160, blank=True, null=True)

    blog = models.CharField(max_length=150, blank=True, null=True)


class ProfileTranslation(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, help_text="Profile")
    lang = models.CharField(
        max_length=5,
        validators=[validate_language_code],
        unique=True,
        help_text="ISO 639-1 language code + ISO 3166-1 alpha-2 country code, e.g. en-US",
    )

    bio = models.CharField(max_length=255)

    def __str__(self) -> str:
        return f"{self.lang}: {self.profile.user.email}"


class UserSetting(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="settings")
    lang = models.CharField(max_length=5, default="en", validators=[validate_language_code])
    main_currency = models.ForeignKey("payments.Currency", on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Capability(models.Model):
    slug = models.SlugField(max_length=40, primary_key=True)
    description = models.CharField(max_length=255, blank=True, null=True, default=None)

    def __str__(self):
        return f"{self.slug}"


class Role(models.Model):
    slug = models.SlugField(max_length=25, primary_key=True)
    name = models.CharField(max_length=255, blank=True, null=True, default=None)
    capabilities = models.ManyToManyField(Capability)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.name} ({self.slug})"


PENDING = "PENDING"
ACCEPTED = "ACCEPTED"
REJECTED = "REJECTED"
WAITING_LIST = "WAITING_LIST"
INVITE_STATUS = (
    (PENDING, "Pending"),
    (REJECTED, "Rejected"),
    (ACCEPTED, "Accepted"),
    (WAITING_LIST, "Waiting list"),
)

PENDING = "PENDING"
DONE = "DONE"
ERROR = "ERROR"
PROCESS_STATUS = (
    (PENDING, "Pending"),
    (DONE, "Done"),
    (ERROR, "Error"),
)


class UserInvite(models.Model):
    _old_status: str
    _email: str

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._old_status = self.status
        self._email = self.email

    email = models.CharField(blank=False, max_length=150, null=True, default=None)

    is_email_validated = models.BooleanField(default=False)
    has_marketing_consent = models.BooleanField(default=False)

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, default=None, blank=True, related_name="invites"
    )
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, null=True, default=None, blank=True)
    syllabus = models.ForeignKey("admissions.Syllabus", on_delete=models.CASCADE, null=True, default=None, blank=True)
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, null=True, default=None, blank=True)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, default=None, blank=True)
    event_slug = models.SlugField(
        max_length=120, blank=True, null=True, help_text="If set, the user signed up because of an Event"
    )
    asset_slug = models.SlugField(
        max_length=60, blank=True, null=True, help_text="If set, the user signed up because of an Asset"
    )

    first_name = models.CharField(max_length=100, default=None, null=True)
    last_name = models.CharField(max_length=100, default=None, null=True)

    token = models.CharField(max_length=255, unique=True)

    author = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, default=None, related_name="invites_by_author"
    )

    status = models.CharField(max_length=15, choices=INVITE_STATUS, default=PENDING)

    process_status = models.CharField(max_length=7, choices=PROCESS_STATUS, default=PENDING)
    process_message = models.CharField(max_length=150, default="")

    phone_regex = RegexValidator(
        regex=r"^\+?1?\d{9,15}$",
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
    )
    phone = models.CharField(
        validators=[phone_regex], max_length=17, blank=True, default=""
    )  # validators should be a list

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    sent_at = models.DateTimeField(default=None, null=True, blank=True)

    country = models.CharField(max_length=30, null=True, default=None, blank=True)
    city = models.CharField(max_length=30, null=True, default=None, blank=True)
    latitude = models.DecimalField(max_digits=30, decimal_places=15, null=True, default=None, blank=True)
    longitude = models.DecimalField(max_digits=30, decimal_places=15, null=True, default=None, blank=True)

    conversion_info = models.JSONField(
        default=None, blank=True, null=True, help_text="UTMs and other conversion information."
    )

    email_quality = models.FloatField(default=None, blank=True, null=True)
    email_status = models.JSONField(default=None, blank=True, null=True)

    def __str__(self):
        return f"Invite for {self.email}"

    def save(self, *args, **kwargs):
        import breathecode.authenticate.tasks as tasks_authenticate

        created = self.pk is None

        status_updated = False
        if created or self._old_status != self.status:
            status_updated = True

        if self.pk and self._email and self.email != self._email:
            raise forms.ValidationError("Email is readonly")

        super().save(*args, **kwargs)  # Call the "real" save() method.

        # this does not work without the created condition due to a bug
        if created and (self.email_quality is None or self.email_status is None):
            tasks_authenticate.async_validate_email_invite.delay(self.id)

        if status_updated:
            signals.invite_status_updated.send_robust(instance=self, sender=UserInvite)

        self._email = self.email
        self._old_status = self.status


INVITED = "INVITED"
ACTIVE = "ACTIVE"
PROFILE_ACADEMY_STATUS = (
    (INVITED, "Invited"),
    (ACTIVE, "Active"),
)


class ProfileAcademy(models.Model):

    def __init__(self, *args, **kwargs):
        super(ProfileAcademy, self).__init__(*args, **kwargs)
        self.__old_status = self.status

    user = models.ForeignKey(User, on_delete=models.SET_NULL, default=None, null=True)

    email = models.CharField(blank=False, max_length=150, null=True, default=None, db_index=True)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    first_name = models.CharField(max_length=100, default=None, null=True, db_index=True)
    last_name = models.CharField(max_length=100, default=None, null=True, db_index=True)
    address = models.CharField(max_length=255, blank=True, default=None, null=True)

    phone_regex = RegexValidator(
        regex=r"^\+?1?\d{9,15}$",
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
    )
    phone = models.CharField(
        validators=[phone_regex], max_length=17, blank=True, default=""
    )  # validators should be a list

    status = models.CharField(max_length=15, choices=PROFILE_ACADEMY_STATUS, default=INVITED, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.email} for academy ({self.academy.name})"

    def save(self, *args, **kwargs):

        if self.__old_status != self.status and self.status == "ACTIVE":
            academy_invite_accepted.send_robust(instance=self, sender=ProfileAcademy)

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
        return f"{self.email} ({self.user.id})"

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()

        return super().save(*args, **kwargs)


class AcademyAuthSettings(models.Model):
    academy = models.OneToOneField(Academy, on_delete=models.CASCADE)
    github_username = models.SlugField(max_length=40, blank=True)
    github_owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        default=None,
        null=True,
        help_text="Github auth token for this user will be used for any admin call to the google cloud api, "
        "for example: inviting users to the academy",
    )
    google_cloud_owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        default=None,
        null=True,
        help_text="Google auth token for this user will be used for any admin call to the google cloud api, "
        "for example: creating classroom video calls",
        related_name="google_cloud_academy_auth_settings",
    )
    github_default_team_ids = models.CharField(
        max_length=40,
        blank=True,
        default="",
        help_text="User will be invited to this github team ID when joining the github organization",
    )
    github_is_sync = models.BooleanField(
        default=False, blank=False, help_text="If true, will try synching users every few hours"
    )
    github_error_log = models.JSONField(
        default=None, blank=True, null=True, help_text="Error trace log for github API communication"
    )
    auto_sync_content = models.BooleanField(
        default=False, help_text="If true, will attempt to create WebhookSubscription on each asset repo"
    )

    def add_error(self, msg):
        if self.github_error_log is None:
            self.github_error_log = []

        thirty_days_old = timezone.now() - timezone.timedelta(days=30)

        def to_datetime(date_str):
            return datetime.fromisoformat(date_str)

        self.github_error_log = [e for e in self.github_error_log if thirty_days_old < to_datetime(e["at"])]

        self.github_error_log.append({"msg": msg, "at": str(timezone.now())})
        self.save()
        return self.github_error_log

    def clean_errors(self, msg):
        self.github_error_log = []
        self.save()
        return self.github_error_log


PENDING = "PENDING"
SYNCHED = "SYNCHED"
UNKNOWN = "UNKNOWN"
PAYMENT_CONFLICT = "PAYMENT_CONFLICT"
STORAGE_STATUS = (
    (PENDING, "Pending"),
    (SYNCHED, "Synched"),
    (ERROR, "Error"),
    (UNKNOWN, "Unknown"),
    (PAYMENT_CONFLICT, "Payment conflict"),
)

ADD = "ADD"
INVITE = "INVITE"
DELETE = "DELETE"
IGNORE = "IGNORE"
STORAGE_ACTION = (
    (ADD, "Add"),
    (DELETE, "Delete"),
    (INVITE, "Invite"),
    (IGNORE, "Ignore"),
)


class GithubAcademyUser(models.Model):

    def __init__(self, *args, **kwargs):
        super(GithubAcademyUser, self).__init__(*args, **kwargs)
        self.__old_status = self.storage_status
        self.__old_action = self.storage_action

    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, default=None, null=True)
    username = models.SlugField(
        max_length=40,
        default=None,
        null=True,
        blank=True,
        help_text="Only used when the username has not been found on 4Geeks",
    )
    storage_status = models.CharField(max_length=20, choices=STORAGE_STATUS, default=PENDING)
    storage_action = models.CharField(max_length=20, choices=STORAGE_ACTION, default=ADD)
    storage_log = models.JSONField(default=None, null=True, blank=True)
    storage_synch_at = models.DateTimeField(default=None, null=True, blank=True)
    # deletion_scheduled_at = models.DateTimeField(default=None, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        if self.user is None:
            return str(self.id) + " " + str(self.username)
        else:
            return str(self.user.email) + " " + str(self.username)

    @staticmethod
    def create_log(msg):
        return {"msg": msg, "at": str(timezone.now())}

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

        if not self.user and (credentials := CredentialsGithub.objects.filter(username=self.username).first()):
            self.user = credentials.user

        exit_op = super().save(*args, **kwargs)

        if has_mutated and self.storage_status == "SYNCHED":
            prev = GithubAcademyUserLog.objects.filter(academy_user=self).order_by("-created_at").first()

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
        return f"{self.user.email} ({self.authed_user})"


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
        return f"Team {str(self.user)}"


class CredentialsQuickBooks(models.Model):
    quibooks_code = models.CharField(max_length=255, primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True)
    quibooks_realmid = models.CharField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


class CredentialsGoogle(models.Model):

    token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255)
    id_token = models.CharField(max_length=1152, default="")
    google_id = models.CharField(max_length=24, default="")
    expires_at = models.DateTimeField()

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


class TokenGetOrCreateArgs(TypedDict, total=False):
    hours_length: int
    expires_at: datetime


class TokenFilterArgs(TypedDict, total=False):
    token_type: str


class Token(rest_framework.authtoken.models.Token):
    """Bearer Token that support different types like `'login'`, `'temporal'` or `'permanent'`."""

    key = models.CharField(max_length=40, db_index=True, unique=True)
    # Foreign key relationship to user for many-to-one relationship
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="auth_token", on_delete=models.CASCADE, verbose_name=_("User")
    )
    token_type = models.CharField(max_length=64, default="temporal", db_index=True)
    expires_at = models.DateTimeField(default=None, blank=True, null=True, db_index=True)

    def save(self, *args, **kwargs):
        without_expire_at = not self.expires_at
        if without_expire_at and self.token_type == "login":
            utc_now = timezone.now()
            self.expires_at = utc_now + LOGIN_TOKEN_LIFETIME

        if without_expire_at and self.token_type == "temporal":
            utc_now = timezone.now()
            self.expires_at = utc_now + TEMPORAL_TOKEN_LIFETIME

        if self.token_type == "one_time" or self.token_type == "permanent":
            self.expires_at = None

        super().save(*args, **kwargs)

    @staticmethod
    def delete_expired_tokens() -> None:
        """Delete expired tokens."""
        utc_now = timezone.now()
        Token.objects.filter(expires_at__lt=utc_now).delete()

    @classmethod
    def get_or_create(cls, user, token_type: str, **kwargs: Unpack[TokenGetOrCreateArgs]) -> Tuple["Token", bool]:
        utc_now = timezone.now()
        kwargs["token_type"] = token_type

        cls.delete_expired_tokens()

        if token_type not in TOKEN_TYPE:
            raise InvalidTokenType(f'Invalid token_type, correct values are {", ".join(TOKEN_TYPE)}')

        has_hours_length = "hours_length" in kwargs
        has_expires_at = "expires_at" in kwargs

        if (token_type == "one_time" or token_type == "permanent") and (has_hours_length or has_expires_at):
            raise BadArguments(
                f"You can't provide token_type='{token_type}' and " "has_hours_length or has_expires_at together"
            )

        if has_hours_length and has_expires_at:
            raise BadArguments("You can't provide hours_length and expires_at argument together")

        if has_hours_length:
            kwargs["expires_at"] = utc_now + timezone.timedelta(hours=kwargs["hours_length"])
            del kwargs["hours_length"]

        token = None
        created = False

        try:
            if token_type == "one_time":
                raise TryToGetOrCreateAOneTimeToken()

            token, created = Token.objects.get_or_create(user=user, **kwargs)

        except MultipleObjectsReturned:
            token = Token.objects.filter(user=user, **kwargs).first()

        except TryToGetOrCreateAOneTimeToken:
            created = True
            token = Token.objects.create(user=user, **kwargs)

        return token, created

    @classmethod
    def get_valid(cls, token: str, async_mode: bool = False, **kwargs: Unpack[TokenFilterArgs]) -> "Token | None":
        utc_now = timezone.now()
        cls.delete_expired_tokens()

        qs = Token.objects.filter(Q(expires_at__gt=utc_now) | Q(expires_at__isnull=True), key=token, **kwargs)
        if async_mode:
            qs = qs.prefetch_related("user")

        # find among any non-expired token
        return qs.first()

    @classmethod
    @sync_to_async
    def aget_valid(cls, token: str, **kwargs: Unpack[TokenFilterArgs]) -> "Token | None":
        return cls.get_valid(token, async_mode=True, **kwargs)

    @classmethod
    def validate_and_destroy(cls, hash: str) -> User:
        token = Token.objects.filter(key=hash, token_type="one_time").first()
        if not token:
            raise TokenNotFound()

        user = token.user
        token.delete()

        return user

    class Meta:
        # ensure user and name are unique
        unique_together = (("user", "key"),)


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
        help_text="If a gitpod user is not connected to a real user and academy in the database, it will be deleted ASAP",
    )


class App(models.Model):
    """
    The only reason for keeping this model is because this model is really indestructible.

    Remove it as soon as Django team let us do it.
    """

    def __init__(self, *args, **kwargs):
        raise DeprecationWarning("authenticate.App was deprecated, use linked_services.App instead")

    name = models.CharField(max_length=25, unique=True, help_text="Descriptive and unique name of the app")
