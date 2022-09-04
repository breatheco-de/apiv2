import hashlib
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from breathecode.admissions.models import Academy, Cohort, Syllabus
import breathecode.certificate.signals as signals

__all__ = ['UserProxy', 'Specialty', 'Badge', 'LayoutDesign', 'UserSpecialty']


class UserProxy(User):

    class Meta:
        proxy = True


class CohortProxy(Cohort):

    class Meta:
        proxy = True


# For example: Full-Stack Web Development
class Specialty(models.Model):
    slug = models.SlugField(max_length=150, unique=True)
    name = models.CharField(max_length=150)
    logo_url = models.CharField(max_length=250, blank=True, null=True, default=None)
    duration_in_hours = models.IntegerField(blank=True, null=True, default=None)
    description = models.TextField(max_length=500, blank=True, null=True, default=None)
    # how long it takes to expire, leave null for unlimited
    expiration_day_delta = models.IntegerField(blank=True, null=True, default=None)

    syllabus = models.OneToOneField(Syllabus,
                                    on_delete=models.CASCADE,
                                    help_text='This specialty represents only one certificate',
                                    blank=True,
                                    null=True,
                                    default=None)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name


# For example: HTML
class Badge(models.Model):
    slug = models.SlugField(max_length=150, unique=True)
    name = models.CharField(max_length=150)
    logo_url = models.CharField(max_length=250, blank=True, null=True, default=None)
    duration_in_hours = models.IntegerField()

    specialties = models.ManyToManyField(Specialty)

    # how long it takes to expire, leave null for unlimited
    expiration_day_delta = models.IntegerField(blank=True, null=True, default=None)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name


class LayoutDesign(models.Model):
    slug = models.SlugField(max_length=150, unique=True)
    name = models.CharField(max_length=40)
    is_default = models.BooleanField(
        default=False,
        help_text='Will be used as default for all future certificates. Only one default layout per academy.')
    html_content = models.TextField(null=True, default=None, blank=True)
    css_content = models.TextField(null=True, default=None, blank=True)

    preview_url = models.CharField(max_length=250, blank=False, null=True, default=None)

    background_url = models.CharField(max_length=250, blank=False, null=False)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


PENDING = 'PENDING'
PERSISTED = 'PERSISTED'
ERROR = 'ERROR'
USER_SPECIALTY_STATUS = (
    (PENDING, 'Pending'),
    (PERSISTED, 'Persisted'),
    (ERROR, 'Error'),
)


class UserSpecialty(models.Model):
    is_cleaned = False

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status_text = models.CharField(max_length=255, default=None, null=True, blank=True)
    status = models.CharField(max_length=15, choices=USER_SPECIALTY_STATUS, default=PENDING)
    specialty = models.ForeignKey(Specialty, on_delete=models.CASCADE)
    token = models.CharField(max_length=40, db_index=True, unique=True)
    expires_at = models.DateTimeField(default=None, blank=True, null=True)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    layout = models.ForeignKey(LayoutDesign, on_delete=models.CASCADE, blank=True, null=True, default=None)
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, blank=True, null=True)
    signed_by = models.CharField(max_length=100)
    signed_by_role = models.CharField(max_length=100, default='Director')
    issued_at = models.DateTimeField(default=None, blank=True, null=True)
    update_hash = models.CharField(max_length=40, blank=True, null=True)

    preview_url = models.CharField(max_length=250, blank=True, null=True, default=None)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def generate_update_hash(self):
        kwargs = {
            'signed_by': self.signed_by,
            'signed_by_role': self.signed_by_role,
            'status': self.status,
            'layout': self.layout,
            'expires_at': self.expires_at,
            'issued_at': self.issued_at,
        }

        important_fields = ['signed_by', 'signed_by_role', 'status', 'layout', 'expires_at', 'issued_at']
        important_values = '-'.join(
            [str(kwargs.get(field) if field in kwargs else None) for field in sorted(important_fields)])

        return hashlib.sha1(important_values.encode('UTF-8')).hexdigest()

    def clean(self):
        if self.status == ERROR:
            return

        if self.cohort is not None and self.cohort.academy.id != self.academy.id:
            raise ValidationError('Cohort academy does not match the specified academy for this certificate')

        utc_now = timezone.now()
        if self.token is None or self.token == '':
            self.token = hashlib.sha1((str(self.user.id) + str(utc_now)).encode('UTF-8')).hexdigest()

        # set expiration
        if self.specialty.expiration_day_delta is not None:
            self.expires_at = utc_now + timezone.timedelta(days=self.specialty.expiration_day_delta)

        self.is_cleaned = True

    def save(self, *args, **kwargs):
        if not self.is_cleaned:
            self.clean()

        hash = self.generate_update_hash()
        self._hash_was_updated = self.update_hash != hash
        self.update_hash = hash

        super().save(*args, **kwargs)  # Call the "real" save() method.

        signals.user_specialty_saved.send(instance=self, sender=self.__class__)
