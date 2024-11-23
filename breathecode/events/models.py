import binascii
import os
import uuid as uuid_lib

from django.contrib.auth.models import User
from django.db import models
from slugify import slugify

from breathecode.admissions.models import Academy, Cohort, CohortTimeSlot, Syllabus
from breathecode.utils.validators.language import validate_language_code

from .signals import event_status_updated, new_event_attendee, new_event_order

PENDING = "PENDING"
PERSISTED = "PERSISTED"
ERROR = "ERROR"
WARNING = "WARNING"
SYNCHED = "SYNCHED"
SYNC_STATUS = (
    (PENDING, "Pending"),
    (PERSISTED, "Persisted"),
    (ERROR, "Error"),
    (WARNING, "Warning"),
    (SYNCHED, "Synched"),
)

__all__ = ["Organization", "Organizer", "Venue", "EventType", "Event", "EventCheckin", "EventbriteWebhook"]


class Organization(models.Model):
    eventbrite_id = models.CharField(unique=True, max_length=30, blank=True)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, blank=True, null=True)
    eventbrite_key = models.CharField(max_length=255, blank=True, null=True, default=None)
    name = models.CharField(max_length=100, blank=True, null=True, default="")

    sync_status = models.CharField(
        max_length=9,
        choices=SYNC_STATUS,
        default=PENDING,
        help_text="One of: PENDING, PERSISTED or ERROR depending on how the eventbrite sync status",
    )
    sync_desc = models.TextField(max_length=255, null=True, default=None, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name or "Nameless"


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
            return self.name + "(" + str(self.id) + ")"
        else:
            return "Organizer " + str(self.id)


ACTIVE = "ACTIVE"
DRAFT = "DRAFT"
DELETED = "DELETED"
VENUE_STATUS = (
    (ACTIVE, "Active"),
    (DRAFT, "Draft"),
    (DELETED, "Deleted"),
)


class Venue(models.Model):
    title = models.CharField(max_length=200, blank=True, default=None, null=True)
    street_address = models.CharField(max_length=250, blank=True, default=None, null=True)
    country = models.CharField(max_length=30, blank=True, default=None, null=True)
    city = models.CharField(max_length=30, blank=True, default=None, null=True)
    latitude = models.DecimalField(max_digits=20, decimal_places=15, default=0)
    longitude = models.DecimalField(max_digits=20, decimal_places=15, default=0)
    state = models.CharField(max_length=30, blank=True, default=None, null=True)
    zip_code = models.CharField(max_length=15, blank=True, default=None, null=True)
    status = models.CharField(max_length=9, choices=VENUE_STATUS, default=DRAFT)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, blank=True, null=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, blank=True, null=True)

    eventbrite_id = models.CharField(unique=True, max_length=80, blank=True, default=None, null=True)
    eventbrite_url = models.CharField(max_length=255, blank=True, default=None, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.title or "No title"


class EventTypeVisibilitySetting(models.Model):
    """
    This will be used to show the workshops, this table point to the resource the user have access, if he/she
    have access, he/she can watch this collection of workshops, the requires hierarchy to see the content
    will be implemented in the view.
    """

    syllabus = models.ForeignKey(Syllabus, on_delete=models.CASCADE, blank=True, null=True)
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, blank=True, null=True)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)

    def __str__(self):
        return f"{str(self.academy)}, {str(self.syllabus)}, {str(self.cohort)}"


class EventType(models.Model):
    slug = models.SlugField(max_length=150, unique=True)
    name = models.CharField(max_length=150)
    description = models.CharField(
        max_length=255, default="", null=False, help_text="This will be publicly shown to 4geeks.com users"
    )
    icon_url = models.URLField(blank=True, null=True, default=None)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, blank=False, null=True)
    lang = models.CharField(max_length=5, default="en", validators=[validate_language_code])
    free_for_bootcamps = models.BooleanField(
        default=True, help_text="Users that belong to other no-saas academies will be able to join without consuming"
    )

    visibility_settings = models.ManyToManyField(
        EventTypeVisibilitySetting, blank=True, help_text="Visibility has to be configured every academy separately"
    )
    allow_shared_creation = models.BooleanField(
        default=True, help_text="Other academies are allowed to create events of this type"
    )

    technologies = models.CharField(
        max_length=200, null=True, default=None, blank=True, help_text="Add comma-separated list of technologies"
    )

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


FINISHED = "FINISHED"
EVENT_STATUS = (
    (ACTIVE, "Active"),
    (DRAFT, "Draft"),
    (DELETED, "Deleted"),
    (FINISHED, "Finished"),
)

USD = "USD"  # United States dollar
CRC = "CRC"  # Costa Rican colón
CLP = "CLP"  # Chilean peso
EUR = "EUR"  # Euro
UYU = "UYU"  # Uruguayan peso
CURRENCIES = (
    (USD, "USD"),
    (CRC, "CRC"),
    (CLP, "CLP"),
    (EUR, "EUR"),
    (UYU, "UYU"),
)


class Event(models.Model):

    def __init__(self, *args, **kwargs):
        super(Event, self).__init__(*args, **kwargs)
        self.__old_status = self.status

    slug = models.SlugField(max_length=150, blank=True, default=None, null=True)
    uuid = models.UUIDField(default=uuid_lib.uuid4, editable=False, unique=True)
    description = models.TextField(max_length=2000, blank=True, default=None, null=True)
    excerpt = models.TextField(max_length=500, blank=True, default=None, null=True)
    asset_slug = models.SlugField(
        max_length=200,
        blank=True,
        default=None,
        null=True,
        help_text="Is the event is about a project, this field will have the asset slug of that project.",
    )
    title = models.CharField(max_length=255, blank=True, default=None, null=True)
    lang = models.CharField(max_length=5, blank=True, default=None, null=True, validators=[validate_language_code])
    currency = models.CharField(max_length=3, choices=CURRENCIES, default=USD, blank=True)
    tags = models.CharField(max_length=100, default="", blank=True)
    free_for_all = models.BooleanField(
        default=False, help_text="Determines if any user (From bootcamp or not) can join the event for free."
    )
    free_for_bootcamps = models.BooleanField(
        default=True,
        blank=True,
        null=True,
        help_text="Determines if users that belong to an academy not available as saas can join the event for free.",
    )

    url = models.URLField(
        max_length=255,
        null=True,
        blank=True,
        default=None,
        help_text="URL can be blank if the event will be synched with EventBrite, it will be filled automatically by the API.",
    )
    banner = models.URLField(max_length=255)
    capacity = models.IntegerField()
    live_stream_url = models.URLField(
        max_length=255,
        null=True,
        blank=True,
        default=None,
        help_text="This URL should have the URL of the meeting if it is an online event, if it's not online it should be empty.",
    )

    starting_at = models.DateTimeField(blank=False)
    ending_at = models.DateTimeField(
        blank=False, help_text="This field contains the value of when the event is supposed to be finished."
    )
    ended_at = models.DateTimeField(
        blank=True,
        null=True,
        default=None,
        help_text="This field contains the value of when the event actually finished.",
    )

    host = models.CharField(
        max_length=100, blank=True, default=None, null=True, help_text="Host name that appear in Eventbrite"
    )
    host_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="event_host",
        help_text="4geeks user that is the host of the event",
    )

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
        help_text="One of: draft, live, started, ended, completed and canceled",
        blank=True,
        default=None,
        null=True,
    )

    sync_with_eventbrite = models.BooleanField(default=False)
    eventbrite_sync_status = models.CharField(
        max_length=9,
        choices=SYNC_STATUS,
        default=PENDING,
        help_text="One of: PENDING, PERSISTED or ERROR depending on how the eventbrite sync status",
    )
    eventbrite_sync_description = models.TextField(max_length=255, null=True, default=None, blank=True)

    published_at = models.DateTimeField(null=True, default=None, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    is_public = models.BooleanField(
        default=True,
        blank=False,
        null=False,
        help_text="If true, then it will be shown in cards and the workshop's landing page. Otherwise it will be hidden.",
    )

    def __str__(self):
        return self.title or "No title"

    def clean(self, *args, **kwargs):
        if self.free_for_all == True:
            self.free_for_bootcamps = True

    def save(self, *args, **kwargs):
        from .signals import event_saved

        status_updated = False
        if self.__old_status != self.status:
            status_updated = True

        created = not self.id

        if self.title and not self.slug:
            self.slug = f"{slugify(self.title).lower()}-{self.uuid}"

        super().save(*args, **kwargs)

        event_saved.send_robust(instance=self, sender=self.__class__, created=created)

        if status_updated:
            event_status_updated.send_robust(instance=self, sender=Event)


PENDING = "PENDING"
DONE = "DONE"
CHECKIN_STATUS = (
    (PENDING, "Pending"),
    (DONE, "Done"),
)


class EventCheckin(models.Model):

    def __init__(self, *args, **kwargs):
        super(EventCheckin, self).__init__(*args, **kwargs)
        self.__old_status = self.status

    email = models.EmailField(max_length=150)

    attendee = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, default=None)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    status = models.CharField(max_length=9, choices=CHECKIN_STATUS, default=PENDING)

    utm_medium = models.CharField(max_length=70, blank=True, null=True, default=None)
    utm_campaign = models.CharField(max_length=70, blank=True, null=True, default=None)
    utm_source = models.CharField(max_length=70, blank=True, null=True, default=None)
    utm_url = models.CharField(max_length=2000, null=True, default=None, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    attended_at = models.DateTimeField(null=True, default=None, blank=True)

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):

        creating = False
        if self.pk is None:
            creating = True

        status_updated = False
        if self.__old_status != self.status:
            status_updated = True

        super().save(*args, **kwargs)

        if creating:
            new_event_order.send_robust(instance=self, sender=EventCheckin)
        elif status_updated and self.status == "DONE":
            new_event_attendee.send_robust(instance=self, sender=EventCheckin)


# PENDING = 'PENDING'
# DONE = 'DONE'
# ERROR='ERROR'
EVENTBRITE_WEBHOOK_STATUS = (
    (PENDING, "Pending"),
    (DONE, "Done"),
    (ERROR, "Error"),
)


class EventbriteWebhook(models.Model):
    api_url = models.CharField(max_length=255, blank=True, null=True, default=None)
    user_id = models.CharField(max_length=20, blank=True, null=True, default=None)
    action = models.CharField(max_length=15, blank=True, null=True, default=None)
    webhook_id = models.CharField(max_length=20, blank=True, null=True, default=None)
    payload = models.JSONField(blank=True, null=True, default=None, help_text="Will be set by async task")
    event = models.ForeignKey(Event, on_delete=models.SET_NULL, blank=True, null=True, default=None)
    attendee = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, default=None)

    organization_id = models.CharField(max_length=20, blank=True, null=True, default=None)
    endpoint_url = models.CharField(max_length=255, blank=True, null=True, default=None)

    status = models.CharField(max_length=9, choices=EVENTBRITE_WEBHOOK_STATUS, default=PENDING)
    status_text = models.CharField(max_length=255, default=None, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"Action {self.action} {self.status} => {self.api_url}"


class LiveClass(models.Model):
    """
    It represents a live class that will be built from a CohortTimeSlot
    """

    cohort_time_slot = models.ForeignKey(CohortTimeSlot, on_delete=models.CASCADE)
    log = models.JSONField(default=dict)
    remote_meeting_url = models.URLField()

    # this should be use in the future to create automatically the permalinks
    hash = models.CharField(max_length=40, unique=True)

    started_at = models.DateTimeField(default=None, blank=True, null=True)
    ended_at = models.DateTimeField(default=None, blank=True, null=True)

    starting_at = models.DateTimeField(db_index=True)
    ending_at = models.DateTimeField(db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def _get_hash(self):
        return binascii.hexlify(os.urandom(20)).decode()

    def save(self, *args, **kwargs):
        if not self.pk:
            self.hash = self._get_hash()

        return super().save(*args, **kwargs)
