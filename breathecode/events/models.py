import os
from django.db import models
from django.contrib.auth.models import User
from breathecode.admissions.models import Academy, Cohort, Syllabus
from breathecode.utils.validation_exception import ValidationException

PENDING = 'PENDING'
PERSISTED = 'PERSISTED'
ERROR = 'ERROR'
WARNING = 'WARNING'
SYNCHED = 'SYNCHED'
SYNC_STATUS = (
    (PENDING, 'Pending'),
    (PERSISTED, 'Persisted'),
    (ERROR, 'Error'),
    (WARNING, 'Warning'),
    (SYNCHED, 'Synched'),
)

__all__ = ['Organization', 'Organizer', 'Venue', 'EventType', 'Event', 'EventCheckin', 'EventbriteWebhook']


class Organization(models.Model):
    eventbrite_id = models.CharField(unique=True, max_length=30, blank=True)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, blank=True, null=True)
    eventbrite_key = models.CharField(max_length=255, blank=True, null=True, default=None)
    name = models.CharField(max_length=100, blank=True, null=True, default='')

    sync_status = models.CharField(
        max_length=9,
        choices=SYNC_STATUS,
        default=PENDING,
        help_text='One of: PENDING, PERSISTED or ERROR depending on how the eventbrite sync status')
    sync_desc = models.TextField(max_length=255, null=True, default=None, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name or 'Nameless'


class Organizer(models.Model):
    eventbrite_id = models.CharField(unique=True, max_length=30, blank=True)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, blank=True, null=True)
    name = models.CharField(max_length=100, blank=True, null=True, default=None)
    description = models.TextField(max_length=500, blank=True, null=True, default=None)

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        if self.name is not None:
            return self.name + '(' + str(self.id) + ')'
        else:
            return 'Organizer ' + str(self.id)


ACTIVE = 'ACTIVE'
DRAFT = 'DRAFT'
DELETED = 'DELETED'
VENUE_STATUS = (
    (ACTIVE, 'Active'),
    (DRAFT, 'Draft'),
    (DELETED, 'Deleted'),
)


class Venue(models.Model):
    title = models.CharField(max_length=200, blank=True, default=None, null=True)
    street_address = models.CharField(max_length=250, blank=True, default=None, null=True)
    country = models.CharField(max_length=30, blank=True, default=None, null=True)
    city = models.CharField(max_length=30, blank=True, default=None, null=True)
    latitude = models.DecimalField(max_digits=20, decimal_places=15, default=0)
    longitude = models.DecimalField(max_digits=20, decimal_places=15, default=0)
    state = models.CharField(max_length=30, blank=True, default=None, null=True)
    zip_code = models.IntegerField(blank=True, default=None, null=True)
    status = models.CharField(max_length=9, choices=VENUE_STATUS, default=DRAFT)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, blank=True, null=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, blank=True, null=True)

    eventbrite_id = models.CharField(unique=True, max_length=80, blank=True, default=None, null=True)
    eventbrite_url = models.CharField(max_length=255, blank=True, default=None, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.title or 'No title'


class EventType(models.Model):
    slug = models.SlugField(max_length=150, unique=True)
    name = models.CharField(max_length=150)
    description = models.CharField(max_length=255, default='', null=False)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, blank=True, null=True)

    shared_with_academies = models.ManyToManyField(Academy,
                                                   blank=True,
                                                   related_name='shared_event_types',
                                                   through='EventTypeAcademy',
                                                   through_fields=('event_type', 'academy'))

    shared_with_syllabus = models.ManyToManyField(Syllabus,
                                                  blank=True,
                                                  through='EventTypeSyllabus',
                                                  through_fields=('event_type', 'syllabus'))

    shared_with_cohorts = models.ManyToManyField(Cohort,
                                                 blank=True,
                                                 through='EventTypeCohort',
                                                 through_fields=('event_type', 'cohort'))

    allow_shared_creation = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name or 'Nameless'


class EventTypeAcademy(models.Model):
    event_type = models.ForeignKey(EventType, on_delete=models.CASCADE)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if EventTypeAcademy.objects.filter(event_type=self.event_type,
                                           academy=self.academy).exclude(id=self.id).exists():
            raise ValidationException('Cannot add a academy twice')

        super().save(*args, **kwargs)


class EventTypeSyllabus(models.Model):
    event_type = models.ForeignKey(EventType, on_delete=models.CASCADE)
    syllabus = models.ForeignKey(Syllabus, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if EventTypeSyllabus.objects.filter(event_type=self.event_type,
                                            syllabus=self.syllabus).exclude(id=self.id).exists():
            raise ValidationException('Cannot add a syllabus twice')

        if not self.event_type.shared_with_cohorts.filter(syllabus_version__syllabus=self.syllabus).exists():
            raise ValidationException(
                'Cannot determine the cohort belong to this syllabus, please add the cohort')

        super().save(*args, **kwargs)


class EventTypeCohort(models.Model):
    """
    The purpose of this model is manage
    """
    event_type = models.ForeignKey(EventType, on_delete=models.CASCADE)
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if EventTypeCohort.objects.filter(event_type=self.event_type,
                                          cohort=self.cohort).exclude(id=self.id).exists():
            raise ValidationException('Cannot add a cohort twice')

        super().save(*args, **kwargs)
        if not self.event_type.shared_with_academies.filter(academy=self.cohort.academy).exists():
            self.event_type.shared_with_academies.add(self.cohort.academy)

        if self.cohort.syllabus_version and not self.event_type.shared_with_academies.filter(
                academy=self.cohort.academy).exists():
            self.event_type.shared_with_syllabus.add(self.cohort.syllabus_version.syllabus)

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)

        if not self.event_type.shared_with_cohorts.filter(academy=self.cohort.academy).exists():
            self.event_type.shared_with_academies.remove(self.cohort.academy)

        if self.cohort.syllabus_version and not self.event_type.shared_with_cohorts.filter(
                syllabus_version__syllabus=self.cohort.syllabus_version.syllabus).exists():
            self.event_type.shared_with_syllabus.remove(self.cohort.syllabus_version.syllabus)


EVENT_STATUS = (
    (ACTIVE, 'Active'),
    (DRAFT, 'Draft'),
    (DELETED, 'Deleted'),
)

USD = 'USD'  # United States dollar
CRC = 'CRC'  # Costa Rican colón
CLP = 'CLP'  # Chilean peso
EUR = 'EUR'  # Euro
UYU = 'UYU'  # Uruguayan peso
CURRENCIES = (
    (USD, 'USD'),
    (CRC, 'CRC'),
    (CLP, 'CLP'),
    (EUR, 'EUR'),
    (UYU, 'UYU'),
)


class Event(models.Model):
    slug = models.SlugField(max_length=150, blank=True, default=None, null=True)
    description = models.TextField(max_length=2000, blank=True, default=None, null=True)
    excerpt = models.TextField(max_length=500, blank=True, default=None, null=True)
    title = models.CharField(max_length=255, blank=True, default=None, null=True)
    lang = models.CharField(max_length=2, blank=True, default=None, null=True)
    currency = models.CharField(max_length=3, choices=CURRENCIES, default=USD, blank=True)
    tags = models.CharField(max_length=100, default='', blank=True)

    url = models.URLField(
        max_length=255,
        null=True,
        blank=True,
        default=None,
        help_text=
        'URL can be blank if the event will be synched with EventBrite, it will be filled automatically by the API.'
    )
    banner = models.URLField(max_length=255)
    capacity = models.IntegerField()

    starting_at = models.DateTimeField(blank=False)
    ending_at = models.DateTimeField(blank=False)

    host = models.CharField(max_length=100, blank=True, default=None, null=True)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, blank=True, null=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, blank=True, null=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)

    online_event = models.BooleanField(default=False)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, null=True, default=None)
    event_type = models.ForeignKey(EventType, on_delete=models.SET_NULL, null=True, default=None)

    eventbrite_id = models.CharField(unique=True, max_length=80, blank=True, default=None, null=True)
    eventbrite_url = models.CharField(max_length=255, blank=True, default=None, null=True)
    eventbrite_organizer_id = models.CharField(max_length=80, blank=True, default=None, null=True)

    status = models.CharField(max_length=9, choices=EVENT_STATUS, default=DRAFT, blank=True)
    eventbrite_status = models.CharField(
        max_length=9,
        help_text='One of: draft, live, started, ended, completed and canceled',
        blank=True,
        default=None,
        null=True)

    sync_with_eventbrite = models.BooleanField(default=False)
    eventbrite_sync_status = models.CharField(
        max_length=9,
        choices=SYNC_STATUS,
        default=PENDING,
        help_text='One of: PENDING, PERSISTED or ERROR depending on how the eventbrite sync status')
    eventbrite_sync_description = models.TextField(max_length=255, null=True, default=None, blank=True)

    published_at = models.DateTimeField(null=True, default=None, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.title or 'No title'

    def save(self, *args, **kwargs):
        from .signals import event_saved

        created = not self.id
        super().save(*args, **kwargs)

        event_saved.send(instance=self, sender=self.__class__, created=created)


PENDING = 'PENDING'
DONE = 'DONE'
CHECKIN_STATUS = (
    (PENDING, 'Pending'),
    (DONE, 'Done'),
)


class EventCheckin(models.Model):
    email = models.EmailField(max_length=150)

    attendee = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, default=None)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    status = models.CharField(max_length=9, choices=CHECKIN_STATUS, default=PENDING)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    attended_at = models.DateTimeField(null=True, default=None, blank=True)

    def __str__(self):
        return self.email


# PENDING = 'PENDING'
# DONE = 'DONE'
# ERROR='ERROR'
EVENTBRITE_WEBHOOK_STATUS = (
    (PENDING, 'Pending'),
    (DONE, 'Done'),
    (ERROR, 'Error'),
)


class EventbriteWebhook(models.Model):
    api_url = models.CharField(max_length=255, blank=True, null=True, default=None)
    user_id = models.CharField(max_length=20, blank=True, null=True, default=None)
    action = models.CharField(max_length=15, blank=True, null=True, default=None)
    webhook_id = models.CharField(max_length=20, blank=True, null=True, default=None)
    organization_id = models.CharField(max_length=20, blank=True, null=True, default=None)
    endpoint_url = models.CharField(max_length=255, blank=True, null=True, default=None)

    status = models.CharField(max_length=9, choices=EVENTBRITE_WEBHOOK_STATUS, default=PENDING)
    status_text = models.CharField(max_length=255, default=None, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'Action {self.action} {self.status} => {self.api_url}'
