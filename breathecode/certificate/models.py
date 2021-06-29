import hashlib
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import JSONField
from breathecode.admissions.models import Academy, Cohort, Certificate


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
    logo_url = models.CharField(max_length=250,
                                blank=True,
                                null=True,
                                default=None)
    duration_in_hours = models.IntegerField(blank=True,
                                            null=True,
                                            default=None)
    description = models.TextField(max_length=500,
                                   blank=True,
                                   null=True,
                                   default=None)
    # how long it takes to expire, leave null for unlimited
    expiration_day_delta = models.IntegerField(blank=True,
                                               null=True,
                                               default=None)

    certificate = models.OneToOneField(
        Certificate,
        on_delete=models.CASCADE,
        help_text="This specialty represents only one certificate",
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
    logo_url = models.CharField(max_length=250,
                                blank=True,
                                null=True,
                                default=None)
    duration_in_hours = models.IntegerField()

    specialties = models.ManyToManyField(Specialty)

    # how long it takes to expire, leave null for unlimited
    expiration_day_delta = models.IntegerField(blank=True,
                                               null=True,
                                               default=None)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name


class LayoutDesign(models.Model):
    slug = models.SlugField(max_length=150, unique=True)
    name = models.CharField(max_length=40)

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
    status_text = models.CharField(max_length=255,
                                   default=None,
                                   null=True,
                                   blank=True)
    status = models.CharField(max_length=15,
                              choices=USER_SPECIALTY_STATUS,
                              default=PENDING)
    specialty = models.ForeignKey(Specialty, on_delete=models.CASCADE)
    token = models.CharField(max_length=40, db_index=True, unique=True)
    expires_at = models.DateTimeField(default=None, blank=True, null=True)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    layout = models.ForeignKey(LayoutDesign,
                               on_delete=models.CASCADE,
                               blank=True,
                               null=True,
                               default=None)
    cohort = models.ForeignKey(Cohort,
                               on_delete=models.CASCADE,
                               blank=True,
                               null=True)
    signed_by = models.CharField(max_length=100)
    signed_by_role = models.CharField(max_length=100, default="Director")

    preview_url = models.CharField(max_length=250,
                                   blank=True,
                                   null=True,
                                   default=None)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def clean(self):
        if self.status == ERROR:
            return

        if self.cohort is not None and self.cohort.academy.id != self.academy.id:
            raise ValidationError(
                "Cohort academy does not match the specified academy for this certificate"
            )

        utc_now = timezone.now()
        if self.token is None or self.token == "":
            self.token = hashlib.sha1(
                (str(self.user.id) +
                 str(utc_now)).encode("UTF-8")).hexdigest()

        # set expiration
        if self.specialty.expiration_day_delta is not None:
            self.expires_at = utc_now + timezone.timedelta(
                days=self.specialty.expiration_day_delta)

        self.is_cleaned = True

    def save(self, *args, **kwargs):
        if not self.is_cleaned:
            self.clean()

        super().save(*args, **kwargs)  # Call the "real" save() method.
