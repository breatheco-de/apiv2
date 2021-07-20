from django.contrib.auth.models import User, Group
from django.conf import settings
from django.db import models
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
import rest_framework.authtoken.models
from django.utils import timezone
from django.core.validators import RegexValidator
from .signals import invite_accepted
from breathecode.admissions.models import Academy, Cohort


class UserProxy(User):
    class Meta:
        proxy = True


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar_url = models.CharField(max_length=255,
                                  blank=True,
                                  null=True,
                                  default=None)
    bio = models.CharField(max_length=255, blank=True, null=True)

    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message=
        "Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone = models.CharField(validators=[phone_regex],
                             max_length=17,
                             blank=True,
                             default='')  # validators should be a list

    show_tutorial = models.BooleanField(
        default=True,
        help_text='Set true if you want to show the tutorial on the user UI/UX'
    )

    twitter_username = models.CharField(max_length=50, blank=True, null=True)
    github_username = models.CharField(max_length=50, blank=True, null=True)
    portfolio_url = models.CharField(max_length=50, blank=True, null=True)
    linkedin_url = models.CharField(max_length=50, blank=True, null=True)

    blog = models.CharField(max_length=150, blank=True, null=True)


class Capability(models.Model):
    slug = models.SlugField(max_length=40, primary_key=True)
    description = models.CharField(max_length=255,
                                   blank=True,
                                   null=True,
                                   default=None)

    def __str__(self):
        return f'{self.slug}'


class Role(models.Model):
    slug = models.SlugField(max_length=25, primary_key=True)
    name = models.CharField(max_length=255,
                            blank=True,
                            null=True,
                            default=None)
    capabilities = models.ManyToManyField(Capability)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.name} ({self.slug})'


PENDING = 'PENDING'
ACCEPTED = 'ACCEPTED'
INVITE_STATUS = (
    (PENDING, 'Pending'),
    (ACCEPTED, 'Accepted'),
)


# TODO: list this invite
class UserInvite(models.Model):

    email = models.CharField(blank=False,
                             max_length=150,
                             null=True,
                             default=None)

    academy = models.ForeignKey(Academy,
                                on_delete=models.CASCADE,
                                null=True,
                                default=None,
                                blank=True)
    cohort = models.ForeignKey(Cohort,
                               on_delete=models.CASCADE,
                               null=True,
                               default=None,
                               blank=True)
    role = models.ForeignKey(Role,
                             on_delete=models.CASCADE,
                             null=True,
                             default=None,
                             blank=True)

    first_name = models.CharField(max_length=100, default=None, null=True)
    last_name = models.CharField(max_length=100, default=None, null=True)

    token = models.CharField(max_length=255, unique=True)

    author = models.ForeignKey(User, on_delete=models.CASCADE)

    status = models.CharField(max_length=15,
                              choices=INVITE_STATUS,
                              default=PENDING)

    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message=
        "Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone = models.CharField(validators=[phone_regex],
                             max_length=17,
                             blank=True,
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

    user = models.ForeignKey(User,
                             on_delete=models.SET_NULL,
                             default=None,
                             null=True)

    email = models.CharField(blank=False,
                             max_length=150,
                             null=True,
                             default=None)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    first_name = models.CharField(max_length=100, default=None, null=True)
    last_name = models.CharField(max_length=100, default=None, null=True)
    address = models.CharField(max_length=255,
                               blank=True,
                               default=None,
                               null=True)

    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message=
        "Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone = models.CharField(validators=[phone_regex],
                             max_length=17,
                             blank=True,
                             default='')  # validators should be a list

    status = models.CharField(max_length=15,
                              choices=PROFILE_ACADEMY_STATUS,
                              default=INVITED)

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
    academy = models.OneToOneField(Academy,
                                   on_delete=models.CASCADE,
                                   blank=True)

    token = models.CharField(max_length=255)
    expires_at = models.DateTimeField()
    facebook_id = models.BigIntegerField(null=True, default=None)
    email = models.CharField(blank=False,
                             null=True,
                             default=None,
                             max_length=150)

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
        # by default token expires one day after
        if self.expires_at == None:
            utc_now = timezone.now()
            if self.token_type == 'login':
                self.expires_at = utc_now + timezone.timedelta(days=1)
            elif self.token_type == 'permanent':
                self.expires_at = None
            else:
                self.expires_at = utc_now + timezone.timedelta(minutes=10)
        super().save(*args, **kwargs)

    @staticmethod
    def get_or_create(user, **kwargs):

        utc_now = timezone.now()
        if "token_type" not in kwargs:
            kwargs["token_type"] = 'temporal'

        if "hours_length" in kwargs:
            kwargs["expires_at"] = utc_now + timezone.timedelta(hours=kwargs["hours_length"])
            del kwargs["hours_length"]

        token, created = Token.objects.get_or_create(user=user, **kwargs)

        if not created:
            if token.expires_at < utc_now:
                token.delete()
                created = True
                token = Token.objects.create(user=user, **kwargs)

        return token, created

    @staticmethod
    def get_valid(token):
        utc_now = timezone.now()
        # delete expired tokens
        Token.objects.filter(expires_at__lt=utc_now).delete()
        # find among any non-expired token
        _token = Token.objects.filter(key=token,
                                      expires_at__gt=utc_now).first()

        return _token

    class Meta:
        # ensure user and name are unique
        unique_together = (('user', 'key'), )


class DeviceId(models.Model):
    name = models.CharField(max_length=40)
    key = models.CharField(max_length=64)
