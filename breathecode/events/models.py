from django.db import models
from django.contrib.auth.models import User
from breathecode.admissions.models import Academy

PENDING = 'PENDING'
PERSISTED = 'PERSISTED'
ERROR = 'ERROR'
SYNC_STATUS = (
    (PENDING, 'Pending'),
    (PERSISTED, 'Persisted'),
    (ERROR, 'Error'),
)


class Organization(models.Model):
    eventbrite_id = models.CharField(unique=True, max_length=30, blank=True)
    academy = models.ForeignKey(Academy,
                                on_delete=models.CASCADE,
                                blank=True,
                                null=True)
    eventbrite_key = models.CharField(max_length=255,
                                      blank=True,
                                      null=True,
                                      default=None)
    name = models.CharField(max_length=100, blank=True, null=True, default='')

    sync_status = models.CharField(
        max_length=9,
        choices=SYNC_STATUS,
        default=PENDING,
        help_text=
        "One of: PENDING, PERSISTED or ERROR depending on how the eventbrite sync status"
    )
    sync_desc = models.TextField(max_length=255,
                                 null=True,
                                 default=None,
                                 blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        if self.name is not None:
            return self.name + "(" + str(self.id) + ")"
        else:
            return "Organization " + str(self.id)


class Organizer(models.Model):
    eventbrite_id = models.CharField(unique=True, max_length=30, blank=True)
    academy = models.ForeignKey(Academy,
                                on_delete=models.CASCADE,
                                blank=True,
                                null=True)
    name = models.CharField(max_length=100,
                            blank=True,
                            null=True,
                            default=None)
    description = models.TextField(max_length=500,
                                   blank=True,
                                   null=True,
                                   default=None)

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        if self.name is not None:
            return self.name + "(" + str(self.id) + ")"
        else:
            return "Organizer " + str(self.id)


ACTIVE = 'ACTIVE'
DRAFT = 'DRAFT'
DELETED = 'DELETED'
VENUE_STATUS = (
    (ACTIVE, 'Active'),
    (DRAFT, 'Draft'),
    (DELETED, 'Deleted'),
)


class Venue(models.Model):
    title = models.CharField(max_length=200,
                             blank=True,
                             default=None,
                             null=True)
    street_address = models.CharField(max_length=250,
                                      blank=True,
                                      default=None,
                                      null=True)
    country = models.CharField(max_length=30,
                               blank=True,
                               default=None,
                               null=True)
    city = models.CharField(max_length=30, blank=True, default=None, null=True)
    latitude = models.DecimalField(max_digits=20, decimal_places=15, default=0)
    longitude = models.DecimalField(max_digits=20,
                                    decimal_places=15,
                                    default=0)
    state = models.CharField(max_length=30,
                             blank=True,
                             default=None,
                             null=True)
    zip_code = models.IntegerField(blank=True, default=None, null=True)
    status = models.CharField(max_length=9,
                              choices=VENUE_STATUS,
                              default=DRAFT)
    academy = models.ForeignKey(Academy,
                                on_delete=models.CASCADE,
                                blank=True,
                                null=True)
    organization = models.ForeignKey(Organization,
                                     on_delete=models.CASCADE,
                                     blank=True,
                                     null=True)

    eventbrite_id = models.CharField(unique=True,
                                     max_length=80,
                                     blank=True,
                                     default=None,
                                     null=True)
    eventbrite_url = models.CharField(max_length=255,
                                      blank=True,
                                      default=None,
                                      null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        if self.title is not None:
            return self.title + "(" + str(self.id) + ")"
        else:
            return "Venue " + str(self.id)


class EventType(models.Model):
    slug = models.SlugField(max_length=150, unique=True)
    name = models.CharField(max_length=150)
    academy = models.ForeignKey(Academy,
                                on_delete=models.CASCADE,
                                blank=True,
                                null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name + "(" + str(self.id) + ")"


EVENT_STATUS = (
    (ACTIVE, 'Active'),
    (DRAFT, 'Draft'),
    (DELETED, 'Deleted'),
)

# Create your models here.


class Event(models.Model):
    description = models.TextField(max_length=2000,
                                   blank=True,
                                   default=None,
                                   null=True)
    excerpt = models.TextField(max_length=500,
                               blank=True,
                               default=None,
                               null=True)
    title = models.CharField(max_length=255,
                             blank=True,
                             default=None,
                             null=True)
    lang = models.CharField(max_length=2, blank=True, default=None, null=True)

    url = models.URLField(max_length=255)
    banner = models.URLField(max_length=255)
    capacity = models.IntegerField()

    starting_at = models.DateTimeField(blank=False)
    ending_at = models.DateTimeField(blank=False)

    host = models.ForeignKey(User,
                             on_delete=models.SET_NULL,
                             related_name='host',
                             blank=True,
                             null=True)
    academy = models.ForeignKey(Academy,
                                on_delete=models.CASCADE,
                                blank=True,
                                null=True)
    organization = models.ForeignKey(Organization,
                                     on_delete=models.CASCADE,
                                     blank=True,
                                     null=True)
    author = models.ForeignKey(User,
                               on_delete=models.SET_NULL,
                               blank=True,
                               null=True)

    online_event = models.BooleanField(default=False)
    venue = models.ForeignKey(Venue,
                              on_delete=models.CASCADE,
                              null=True,
                              default=None)
    event_type = models.ForeignKey(EventType,
                                   on_delete=models.SET_NULL,
                                   null=True,
                                   default=None)

    eventbrite_id = models.CharField(unique=True,
                                     max_length=80,
                                     blank=True,
                                     default=None,
                                     null=True)
    eventbrite_url = models.CharField(max_length=255,
                                      blank=True,
                                      default=None,
                                      null=True)
    eventbrite_organizer_id = models.CharField(max_length=80,
                                               blank=True,
                                               default=None,
                                               null=True)

    status = models.CharField(max_length=9,
                              choices=EVENT_STATUS,
                              default=DRAFT,
                              blank=True)
    eventbrite_status = models.CharField(
        max_length=9,
        help_text="One of: draft, live, started, ended, completed and canceled",
        blank=True,
        default=None,
        null=True)

    sync_status = models.CharField(
        max_length=9,
        choices=SYNC_STATUS,
        default=PENDING,
        help_text=
        "One of: PENDING, PERSISTED or ERROR depending on how the eventbrite sync status"
    )
    sync_desc = models.TextField(max_length=255,
                                 null=True,
                                 default=None,
                                 blank=True)

    published_at = models.DateTimeField(null=True, default=None, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        if self.title is not None:
            return self.title + "(" + str(self.id) + ")"
        else:
            return "Event " + str(self.id)


PENDING = 'PENDING'
DONE = 'DONE'
CHECKIN_STATUS = (
    (PENDING, 'Pending'),
    (DONE, 'Done'),
)


class EventCheckin(models.Model):
    email = models.EmailField(max_length=150)

    attendee = models.ForeignKey(User,
                                 on_delete=models.CASCADE,
                                 blank=True,
                                 null=True,
                                 default=None)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    status = models.CharField(max_length=9,
                              choices=CHECKIN_STATUS,
                              default=PENDING)

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
    api_url = models.CharField(max_length=255,
                               blank=True,
                               null=True,
                               default=None)
    user_id = models.CharField(max_length=20,
                               blank=True,
                               null=True,
                               default=None)
    action = models.CharField(max_length=15,
                              blank=True,
                              null=True,
                              default=None)
    webhook_id = models.CharField(max_length=20,
                                  blank=True,
                                  null=True,
                                  default=None)
    organization_id = models.CharField(max_length=20,
                                       blank=True,
                                       null=True,
                                       default=None)
    endpoint_url = models.CharField(max_length=255,
                                    blank=True,
                                    null=True,
                                    default=None)

    status = models.CharField(max_length=9,
                              choices=EVENTBRITE_WEBHOOK_STATUS,
                              default=PENDING)
    status_text = models.CharField(max_length=255,
                                   default=None,
                                   null=True,
                                   blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'Action {self.action} {self.status} => {self.api_url}'
