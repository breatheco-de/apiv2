import os
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from .signals import student_edu_status_updated

GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', None)


def get_user_label(self):
    return f'{self.first_name} {self.last_name} ({self.email})'


User.add_to_class('__str__', get_user_label)

__all__ = [
    'UserAdmissions', 'Country', 'City', 'Academy', 'Certificate', 'AcademyCertificate', 'Syllabus', 'Cohort',
    'CohortUser', 'CertificateTimeSlot', 'CohortTimeSlot'
]


class UserAdmissions(User):
    class Meta:
        proxy = True


class Country(models.Model):
    code = models.CharField(max_length=3, primary_key=True)
    name = models.CharField(max_length=30)

    def __str__(self):
        return f'{self.name} ({self.code})'


class City(models.Model):
    name = models.CharField(max_length=30)
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
    slug = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=150)
    logo_url = models.CharField(max_length=255)
    icon_url = models.CharField(max_length=255,
                                help_text='It has to be a square',
                                default='/static/icons/picture.png')
    website_url = models.CharField(max_length=255, blank=True, null=True, default=None)

    street_address = models.CharField(max_length=250)

    marketing_email = models.EmailField(blank=True, null=True, default=None)
    feedback_email = models.EmailField(blank=True, null=True, default=None)

    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    marketing_phone = models.CharField(validators=[phone_regex],
                                       max_length=17,
                                       blank=True,
                                       null=True,
                                       default=None)  # validators should be a list

    twitter_handle = models.CharField(max_length=15, blank=True, null=True, default=None)
    facebook_handle = models.CharField(max_length=30, blank=True, null=True, default=None)
    instagram_handle = models.CharField(max_length=30, blank=True, null=True, default=None)
    github_handle = models.CharField(max_length=20, blank=True, null=True, default=None)
    linkedin_url = models.URLField(blank=True, null=True, default=None)
    youtube_url = models.URLField(blank=True, null=True, default=None)

    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    zip_code = models.IntegerField(blank=True, null=True)

    active_campaign_slug = models.SlugField(max_length=100, unique=False, null=True, default=None)

    status = models.CharField(max_length=15, choices=ACADEMY_STATUS, default=ACTIVE)

    timezone = models.CharField(max_length=50, null=True, default=None)

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

    def save(self, *args, **kwargs):
        from .actions import get_bucket_object
        if os.getenv('ENV', '') == 'production':
            obj = get_bucket_object(f'location-{self.slug}')
            if obj is not None:
                self.logo_url = obj.public_url

        super().save(*args, **kwargs)  # Call the "real" save() method.


PARTIME = 'PART-TIME'
FULLTIME = 'FULL-TIME'
SCHEDULE_TYPE = (
    (PARTIME, 'Part-Time'),
    (FULLTIME, 'Full-Time'),
)


class Syllabus(models.Model):
    slug = models.SlugField(max_length=100, blank=True, null=True, default=None)
    name = models.CharField(max_length=150, blank=True, null=True, default=None)
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
    private = models.BooleanField(default=False)

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


class SyllabusVersion(models.Model):
    json = models.JSONField()

    version = models.PositiveSmallIntegerField()
    syllabus = models.ForeignKey(Syllabus, on_delete=models.CASCADE)
    status = models.CharField(max_length=15, choices=VERSION_STATUS, default=PUBLISHED)
    change_log_details = models.TextField(max_length=450, blank=True, null=True, default=None)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.syllabus.slug}.v{self.version}'


class SyllabusSchedule(models.Model):
    name = models.CharField(max_length=150)

    schedule_type = models.CharField(max_length=15, choices=SCHEDULE_TYPE, default='PART-TIME')
    description = models.TextField(max_length=450)

    syllabus = models.ForeignKey(Syllabus, on_delete=models.CASCADE, default=None, null=True)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, default=None, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name

    # def delete(self, *args, **kwargs):
    #     remove_bucket_object("certificate-logo-"+self.slug)
    #     super(Image, self).delete(*args, **kwargs)

    # def save(self, *args, **kwargs):

    #     if GOOGLE_APPLICATION_CREDENTIALS is not None and GOOGLE_APPLICATION_CREDENTIALS != '':
    #         obj = get_bucket_object('certificate-logo-' + self.slug)
    #         if obj is not None:
    #             self.logo = obj.public_url

    #     super().save(*args, **kwargs)  # Call the "real" save() method.


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
    slug = models.CharField(max_length=150, unique=True)
    name = models.CharField(max_length=150)

    kickoff_date = models.DateTimeField()
    ending_date = models.DateTimeField(blank=True, null=True)
    current_day = models.IntegerField(
        help_text='Each day the teacher takes attendancy and increases the day in one')
    current_module = models.IntegerField(
        null=True,
        default=None,
        blank=True,
        help_text=
        'The syllabus is separated by modules, from 1 to N and the teacher decides when to start a new mobule (after a couple of days)'
    )
    stage = models.CharField(max_length=15, choices=COHORT_STAGE, default=INACTIVE)
    private = models.BooleanField(default=False)
    never_ends = models.BooleanField(default=False)

    remote_available = models.BooleanField(
        default=True, help_text='True (default) if the students from other cities can take it from home')
    online_meeting_url = models.URLField(max_length=255, blank=True, default=None, null=True)

    timezone = models.CharField(max_length=50, null=True, default=None)

    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)

    syllabus_version = models.ForeignKey(SyllabusVersion, on_delete=models.SET_NULL, default=None, null=True)
    schedule = models.ForeignKey(SyllabusSchedule, on_delete=models.SET_NULL, default=None, null=True)

    language = models.CharField(max_length=2, default='en')

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name + '(' + self.slug + ')'

    def save(self, *args, **kwargs):
        from .signals import cohort_saved

        created = not self.id
        super().save(*args, **kwargs)

        cohort_saved.send(instance=self, sender=self.__class__, created=created)


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
    role = models.CharField(max_length=9, choices=COHORT_ROLE, default=STUDENT)

    finantial_status = models.CharField(max_length=15, choices=FINANTIAL_STATUS, default=None, null=True)
    educational_status = models.CharField(max_length=15, choices=EDU_STATUS, default=None, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def save(self, *args, **kwargs):

        if self.__old_edu_status != self.educational_status:
            student_edu_status_updated.send(instance=self, sender=CohortUser)

        super().save(*args, **kwargs)  # Call the "real" save() method.


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
date_interger_description = ('The first 4 number are year, the next 2 number are month, the next 2 number '
                             'are day, the next 2 number are hour and the last 2 number are second')


class TimeSlot(models.Model):
    starting_at = models.BigIntegerField(
        help_text=date_interger_description,
        default=202101010000,
        validators=[
            MaxValueValidator(300000000000),  # year 3000
            MinValueValidator(202101010000),  # year 2021, month 1 and day 1
        ])

    ending_at = models.BigIntegerField(
        help_text=date_interger_description,
        default=202101010000,
        validators=[
            MaxValueValidator(300000000000),  # year 3000
            MinValueValidator(202101010000),  # year 2021, month 1 and day 1
        ])

    timezone = models.CharField(max_length=50, default='America/New_York')
    recurrent = models.BooleanField(default=True)
    recurrency_type = models.CharField(max_length=10, choices=RECURRENCY_TYPE, default=WEEKLY)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True


class SyllabusScheduleTimeSlot(TimeSlot):
    schedule = models.ForeignKey(SyllabusSchedule, on_delete=models.CASCADE)


class CohortTimeSlot(TimeSlot):
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE)
