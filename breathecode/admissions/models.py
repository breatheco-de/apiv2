import base64
import hashlib
import json
import logging
import os

from django import forms
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models

from . import signals
from .signals import syllabus_version_json_updated

GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', None)
logger = logging.getLogger(__name__)


def get_user_label(self):
    return f'{self.first_name} {self.last_name} ({self.email})'


User.add_to_class('__str__', get_user_label)

__all__ = ['UserAdmissions', 'Country', 'City', 'Academy', 'Syllabus', 'Cohort', 'CohortUser', 'CohortTimeSlot']


class UserAdmissions(User):

    class Meta:
        proxy = True


class Country(models.Model):
    code = models.CharField(max_length=3, primary_key=True, db_index=True)
    name = models.CharField(max_length=30, db_index=True)

    def __str__(self):
        return f'{self.name} ({self.code})'


class City(models.Model):
    name = models.CharField(max_length=30, db_index=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


INACTIVE = 'INACTIVE'
ACTIVE = 'ACTIVE'
DELETED = 'DELETED'
ACADEMY_STATUS = (
    (INACTIVE, 'Inactive'),
    (ACTIVE, 'Active'),
    (DELETED, 'Deleted'),
)


class Academy(models.Model):

    def __init__(self, *args, **kwargs):
        super(Academy, self).__init__(*args, **kwargs)
        self.__old_slug = self.slug

    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=150, db_index=True)
    legal_name = models.CharField(max_length=150, db_index=True, default=None, null=True, blank=True)
    logo_url = models.CharField(max_length=255)
    icon_url = models.CharField(max_length=255, help_text='It has to be a square', default='/static/icons/picture.png')
    website_url = models.CharField(max_length=255, blank=True, null=True, default=None)
    white_label_url = models.CharField(max_length=255, blank=True, null=True, default=None)

    street_address = models.CharField(max_length=250)

    marketing_email = models.EmailField(blank=True, null=True, default=None)
    feedback_email = models.EmailField(blank=True, null=True, default=None)

    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    marketing_phone = models.CharField(validators=[phone_regex], max_length=17, blank=True, null=True,
                                       default=None)  # validators should be a list

    twitter_handle = models.CharField(max_length=15, blank=True, null=True, default=None)
    facebook_handle = models.CharField(max_length=30, blank=True, null=True, default=None)
    instagram_handle = models.CharField(max_length=30, blank=True, null=True, default=None)
    github_handle = models.CharField(max_length=20, blank=True, null=True, default=None)
    linkedin_url = models.URLField(blank=True, null=True, default=None)
    youtube_url = models.URLField(blank=True, null=True, default=None)

    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, db_index=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, db_index=True)
    zip_code = models.IntegerField(blank=True, null=True, db_index=True)
    white_labeled = models.BooleanField(default=False)

    active_campaign_slug = models.SlugField(max_length=100,
                                            unique=False,
                                            null=True,
                                            default=None,
                                            blank=True,
                                            db_index=True)

    available_as_saas = models.BooleanField(default=False,
                                            help_text='Academies available as SAAS will be sold thru 4Geeks.com',
                                            db_index=True)

    is_hidden_on_prework = models.BooleanField(
        default=True,
        null=False,
        blank=False,
        help_text='Determines if the cohorts will be shown in the dashboard if it\'s status is \'PREWORK\'',
        db_index=True)

    status = models.CharField(max_length=15, choices=ACADEMY_STATUS, default=ACTIVE, db_index=True)
    main_currency = models.ForeignKey('payments.Currency',
                                      on_delete=models.CASCADE,
                                      null=True,
                                      blank=True,
                                      related_name='+')

    timezone = models.CharField(max_length=50, null=True, default=None, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    logistical_information = models.CharField(max_length=150, blank=True, null=True)

    def default_ac_slug(self):
        return self.slug

    def __str__(self):
        return self.name

    # def delete(self, *args, **kwargs):
    #     remove_bucket_object("location-"+self.slug)
    #     super(Image, self).delete(*args, **kwargs)

    def clean(self):
        if self.status:
            self.status = self.status.upper()

    def save(self, *args, **kwargs):
        from .actions import get_bucket_object
        from .signals import academy_saved

        self.full_clean()
        created = not self.id

        if os.getenv('ENV', '') == 'production':
            obj = get_bucket_object(f'location-{self.slug}')
            if obj is not None:
                self.logo_url = obj.public_url

        if not created and self.__old_slug != self.slug:
            raise Exception('Academy slug cannot be updated')

        super().save(*args, **kwargs)  # Call the "real" save() method.

        if created:
            self.__old_slug = self.slug

        academy_saved.send(instance=self, sender=self.__class__, created=created)


PARTIME = 'PART-TIME'
FULLTIME = 'FULL-TIME'
SCHEDULE_TYPE = (
    (PARTIME, 'Part-Time'),
    (FULLTIME, 'Full-Time'),
)


class Syllabus(models.Model):
    slug = models.SlugField(max_length=100, blank=True, null=True, default=None, db_index=True)
    name = models.CharField(max_length=150, blank=True, null=True, default=None, db_index=True)
    main_technologies = models.CharField(max_length=150,
                                         blank=True,
                                         null=True,
                                         default=None,
                                         help_text='Coma separated, E.g: HTML, CSS, Javascript')

    github_url = models.URLField(max_length=255, blank=True, null=True, default=None)
    duration_in_hours = models.IntegerField(null=True, default=None)
    duration_in_days = models.IntegerField(null=True, default=None)
    week_hours = models.IntegerField(null=True, default=None)
    logo = models.CharField(max_length=250, blank=True, null=True, default=None)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    # by default a syllabus can be re-used by any other academy
    private = models.BooleanField(default=False, db_index=True)
    is_documentation = models.BooleanField(default=False, db_index=True)

    # a syllabus can be shared with other academy, but only the academy owner can update or delete it
    academy_owner = models.ForeignKey(Academy, on_delete=models.CASCADE, null=True, default=None)

    def __str__(self):
        return self.slug if self.slug else 'unknown'


PUBLISHED = 'PUBLISHED'
DRAFT = 'DRAFT'
VERSION_STATUS = (
    (PUBLISHED, 'Published'),
    (DRAFT, 'Draft'),
)

ERROR = 'ERROR'
OK = 'OK'
PENDING = 'PENDING'
WARNING = 'WARNING'
INTEGRITY_STATUS = (
    (ERROR, 'Error'),
    (PENDING, 'Pending'),
    (WARNING, 'Warning'),
    (OK, 'Ok'),
)


class SyllabusVersion(models.Model):
    json = models.JSONField()

    version = models.PositiveSmallIntegerField(db_index=True)
    syllabus = models.ForeignKey(Syllabus, on_delete=models.CASCADE)
    status = models.CharField(max_length=15, choices=VERSION_STATUS, default=PUBLISHED, db_index=True)
    change_log_details = models.TextField(max_length=450, blank=True, null=True, default=None)

    integrity_status = models.CharField(max_length=15, choices=INTEGRITY_STATUS, default=PENDING, db_index=True)
    integrity_check_at = models.DateTimeField(null=True, blank=True, default=None, db_index=True)
    integrity_report = models.JSONField(null=True, blank=True, default=None)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __init__(self, *args, **kwargs):
        super(SyllabusVersion, self).__init__(*args, **kwargs)
        self.__json_hash = self.hashed_json()

    def __str__(self):
        return f'{self.syllabus.slug}.v{self.version}'

    def hashed_json(self):
        if self.json is None:
            return ''

        encoded = base64.b64encode(json.dumps(self.json, sort_keys=True).encode('utf-8'))
        return hashlib.sha256(encoded).hexdigest()

    def save(self, *args, **kwargs):

        json_modified = False

        if self.__json_hash != self.hashed_json():
            json_modified = True

        super().save(*args, **kwargs)

        if json_modified: syllabus_version_json_updated.send(instance=self, sender=SyllabusVersion)


class SyllabusSchedule(models.Model):
    name = models.CharField(max_length=150, db_index=True)

    schedule_type = models.CharField(max_length=15, choices=SCHEDULE_TYPE, default='PART-TIME', db_index=True)
    description = models.TextField(max_length=450, db_index=True)

    syllabus = models.ForeignKey(Syllabus, on_delete=models.CASCADE, default=None, null=True)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, default=None, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name


INACTIVE = 'INACTIVE'
PREWORK = 'PREWORK'
STARTED = 'STARTED'
FINAL_PROJECT = 'FINAL_PROJECT'
ENDED = 'ENDED'
DELETED = 'DELETED'
COHORT_STAGE = (
    (INACTIVE, 'Inactive'),
    (PREWORK, 'Prework'),
    (STARTED, 'Started'),
    (FINAL_PROJECT, 'Final Project'),
    (ENDED, 'Ended'),
    (DELETED, 'Deleted'),
)


class Cohort(models.Model):
    _current_history_log = None
    _old_stage = None

    slug = models.CharField(max_length=150, unique=True, db_index=True)
    name = models.CharField(max_length=150, db_index=True)

    kickoff_date = models.DateTimeField(db_index=True)
    ending_date = models.DateTimeField(blank=True, null=True, db_index=True)
    current_day = models.IntegerField(help_text='Each day the teacher takes attendancy and increases the day in one',
                                      default=1)
    current_module = models.IntegerField(
        null=True,
        default=None,
        blank=True,
        help_text=
        'The syllabus is separated by modules, from 1 to N and the teacher decides when to start a new mobule (after a couple of days)'
    )
    stage = models.CharField(max_length=15, choices=COHORT_STAGE, default=INACTIVE, db_index=True)
    private = models.BooleanField(
        default=False,
        help_text='It will not show on the public API endpoints but you will still be able to add people manually',
        db_index=True)
    accepts_enrollment_suggestions = models.BooleanField(
        default=True, help_text='The system will suggest won leads to be added to this cohort', db_index=True)

    never_ends = models.BooleanField(default=False, db_index=True)

    remote_available = models.BooleanField(
        default=True, help_text='True (default) if the students from other cities can take it from home', db_index=True)
    online_meeting_url = models.URLField(max_length=255, blank=True, default=None, null=True)

    timezone = models.CharField(max_length=50, null=True, default=None, blank=True, db_index=True)

    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)

    history_log = models.JSONField(
        default=None,
        blank=True,
        null=True,
        help_text='The cohort history will save attendancy and information about progress on each class')

    syllabus_version = models.ForeignKey(SyllabusVersion,
                                         on_delete=models.SET_NULL,
                                         default=None,
                                         null=True,
                                         blank=True)

    intro_video = models.URLField(null=True, blank=True, default=None)
    schedule = models.ForeignKey(SyllabusSchedule, on_delete=models.SET_NULL, default=None, null=True, blank=True)

    is_hidden_on_prework = models.BooleanField(
        default=True,
        null=True,
        blank=True,
        help_text='Determines if the cohort will be shown in the dashboard if it\'s status is \'PREWORK\'',
        db_index=True)

    available_as_saas = models.BooleanField(
        default=False,
        null=True,
        blank=True,
        help_text='Cohorts available as SAAS will be sold through plans at 4Geeks.com',
        db_index=True)

    language = models.CharField(max_length=2, default='en', db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_history_log = self.history_log
        self._old_stage = self.stage

    def clean(self):
        if self.stage:
            self.stage = self.stage.upper()

        if self.never_ends and self.ending_date:
            raise forms.ValidationError('If the cohort never ends, it cannot have ending date')

        if not self.kickoff_date:
            raise forms.ValidationError('Kickoff date is required')

    def save_history_log(self, *args, **kwargs):
        """
        It prevent to trigger cohort_log_saved signal when the cohort is created, you must avoid to use this
        method.
        """
        assert self.id

        self.full_clean()

        super().save(*args, **kwargs)

        signals.cohort_saved.send(instance=self, sender=self.__class__, created=False)

        self._current_history_log = self.history_log

    def save(self, *args, **kwargs):

        created = not self.id

        self.full_clean()

        stage_updated = False
        if self.pk is None or self._old_stage != self.stage:
            stage_updated = True

        super().save(*args, **kwargs)

        signals.cohort_saved.send(instance=self, sender=self.__class__, created=created)

        if self.history_log and self.history_log != self._current_history_log:
            signals.cohort_log_saved.send(instance=self, sender=self.__class__, created=created)

        if stage_updated:
            signals.cohort_stage_updated.send(instance=self, sender=self.__class__)

        self._current_history_log = self.history_log

    def __str__(self):
        return self.name + '(' + self.slug + ')'


TEACHER = 'TEACHER'
ASSISTANT = 'ASSISTANT'
STUDENT = 'STUDENT'
REVIEWER = 'REVIEWER'
COHORT_ROLE = (
    (TEACHER, 'Teacher'),
    (ASSISTANT, 'Assistant'),
    (REVIEWER, 'Reviewer'),
    (STUDENT, 'Student'),
)

FULLY_PAID = 'FULLY_PAID'
UP_TO_DATE = 'UP_TO_DATE'
LATE = 'LATE'
FINANTIAL_STATUS = (
    (FULLY_PAID, 'Fully Paid'),
    (UP_TO_DATE, 'Up to date'),
    (LATE, 'Late'),
)

ACTIVE = 'ACTIVE'
POSTPONED = 'POSTPONED'
SUSPENDED = 'SUSPENDED'
GRADUATED = 'GRADUATED'
DROPPED = 'DROPPED'
EDU_STATUS = (
    (ACTIVE, 'Active'),
    (POSTPONED, 'Postponed'),
    (GRADUATED, 'Graduated'),
    (SUSPENDED, 'Suspended'),
    (DROPPED, 'Dropped'),
)


class CohortUser(models.Model):

    def __init__(self, *args, **kwargs):
        super(CohortUser, self).__init__(*args, **kwargs)
        self.__old_edu_status = self.educational_status

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE)
    role = models.CharField(max_length=9, choices=COHORT_ROLE, default=STUDENT, db_index=True)

    watching = models.BooleanField(default=False,
                                   help_text='You can active students to the watch list and monitor them closely',
                                   db_index=True)

    history_log = models.JSONField(
        default=dict,
        blank=True,
        null=False,
        help_text='The cohort user log will save attendancy and information about progress on each class')

    #FIXME: this have a typo
    finantial_status = models.CharField(max_length=15,
                                        choices=FINANTIAL_STATUS,
                                        default=None,
                                        null=True,
                                        blank=True,
                                        db_index=True)

    educational_status = models.CharField(max_length=15,
                                          choices=EDU_STATUS,
                                          default=ACTIVE,
                                          null=True,
                                          blank=True,
                                          db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def clean(self):
        if self.role:
            self.role = self.role.upper()

        if self.finantial_status:
            self.finantial_status = self.finantial_status.upper()

        if self.educational_status:
            self.educational_status = self.educational_status.upper()

    def save(self, *args, **kwargs):
        # check the fields before saving
        self.full_clean()
        on_create = self.pk is None

        # If the CohortUser is being created (Not modified)
        if on_create and self.educational_status is None:
            self.educational_status = ACTIVE

        edu_status_updated = False
        if on_create or self.__old_edu_status != self.educational_status:
            edu_status_updated = True

        result = super().save(*args, **kwargs)  # Call the "real" save() method.

        if edu_status_updated:
            signals.student_edu_status_updated.send(instance=self, sender=self.__class__)

        signals.cohort_log_saved.send(instance=self, sender=self.__class__)

        if on_create:
            signals.cohort_user_created.send(instance=self, sender=self.__class__)

        self.__old_edu_status = self.educational_status

        return result


DAILY = 'DAILY'
WEEKLY = 'WEEKLY'
MONTHLY = 'MONTHLY'
# YEARLY = 'YEARLY'
RECURRENCY_TYPE = (
    (DAILY, 'Daily'),
    (WEEKLY, 'Weekly'),
    (MONTHLY, 'Monthly'),
    # (YEARLY, 'Yearly'),
)

# YYYYMMDDHHMM
date_integer_description = ('The first 4 number are year, the next 2 number are month, the next 2 number '
                            'are day, the next 2 number are hour and the last 2 number are second')


class TimeSlot(models.Model):
    starting_at = models.BigIntegerField(
        help_text=date_integer_description,
        default=202101010000,
        validators=[
            MaxValueValidator(300000000000),  # year 3000
            MinValueValidator(202101010000),  # year 2021, month 1 and day 1
        ],
        db_index=True)

    ending_at = models.BigIntegerField(
        help_text=date_integer_description,
        default=202101010000,
        validators=[
            MaxValueValidator(300000000000),  # year 3000
            MinValueValidator(202101010000),  # year 2021, month 1 and day 1
        ],
        db_index=True)

    timezone = models.CharField(max_length=50, default='America/New_York', db_index=True)
    recurrent = models.BooleanField(default=True, db_index=True)
    recurrency_type = models.CharField(max_length=10, choices=RECURRENCY_TYPE, default=WEEKLY, db_index=True)

    removed_at = models.DateTimeField(null=True,
                                      default=None,
                                      blank=True,
                                      help_text='This will be available until this date',
                                      db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True


class SyllabusScheduleTimeSlot(TimeSlot):
    schedule = models.ForeignKey(SyllabusSchedule, on_delete=models.CASCADE)

    def clean(self):
        if self.recurrency_type:
            self.recurrency_type = self.recurrency_type.upper()

        if self.starting_at > self.ending_at:
            raise forms.ValidationError('The starting date must be before the ending date')

    def save(self, *args, **kwargs):
        # created = not self.id

        self.full_clean()
        super().save(*args, **kwargs)

        # signals.timeslot_saved.send(instance=self, sender=self.__class__, created=created)


class CohortTimeSlot(TimeSlot):
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE)

    def clean(self):
        if self.recurrency_type:
            self.recurrency_type = self.recurrency_type.upper()

        if self.starting_at > self.ending_at:
            raise forms.ValidationError('The starting date must be before the ending date')

    def save(self, *args, **kwargs):
        created = not self.id

        self.full_clean()
        super().save(*args, **kwargs)

        signals.timeslot_saved.send(instance=self, sender=self.__class__, created=created)
