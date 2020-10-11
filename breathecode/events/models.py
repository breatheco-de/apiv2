from django.db import models
from django.contrib.auth.models import User
from breathecode.admissions.models import Academy

class Organizacion(models.Model):
    eventbrite_id = models.CharField(unique=True, max_length=30, blank=True)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, blank=True, null=True)
    eventbrite_key = models.CharField(max_length=255, blank=True, null=True, default=None)
    name = models.CharField(max_length=100, blank=True, null=True, default=None)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

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
    organization = models.ForeignKey(Organizacion, on_delete=models.CASCADE, blank=True, null=True)
    
    eventbrite_id = models.CharField(unique=True, max_length=80, blank=True, default=None, null=True)
    eventbrite_url = models.CharField(max_length=255, blank=True, default=None, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.title

class EventType(models.Model):
    slug = models.SlugField(max_length=150, unique=True)
    name = models.CharField(max_length=150)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name

EVENT_STATUS = (
    (ACTIVE, 'Active'),
    (DRAFT, 'Draft'),
    (DELETED, 'Deleted'),
)
# Create your models here.
class Event(models.Model):
    slug = models.SlugField(max_length=150, unique=True)

    description = models.TextField(max_length=2000)
    exerpt = models.TextField(max_length=500)
    title = models.CharField(max_length=255)
    lang = models.CharField(max_length=2)
    
    url = models.URLField(max_length=255)
    banner = models.URLField(max_length=255)
    capacity = models.IntegerField()

    starting_at = models.DateTimeField(blank=False)
    ending_at = models.DateTimeField(blank=False)

    host = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='host', blank=True, null=True)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, blank=True, null=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)

    event_type = models.ForeignKey(EventType, on_delete=models.SET_NULL, null=True, default=None)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, null=True, default=None)

    status = models.CharField(max_length=9,choices=EVENT_STATUS,default=DRAFT,blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.title

class EventCheckin(models.Model):
    email = models.EmailField(max_length=150)

    attendee = models.ForeignKey(User, on_delete=models.CASCADE, blank=True)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.email