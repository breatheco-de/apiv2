from django.db import models
from phonenumber_field.modelfields import PhoneNumberField

STRONG = 'STRONG'
SOFT = 'SOFT'
DISCOVERY = 'DISCOVERY'
OTHER = 'OTHER'
TAG_TYPE = (
    (STRONG, 'Strong'),
    (SOFT, 'Soft'),
    (DISCOVERY, 'Discovery'),
    (OTHER, 'Other'),
)
class Tag(models.Model):
    slug = models.CharField(max_length=150, unique=True)
    tag_type = models.CharField(max_length=15, choices=TAG_TYPE, null=True, default=None, help_text="This will be use to determine the type of lead (strong, soft, etc.), if a lead has a tag with type=strong it will be added to the automation for strong leads")
    acp_id = models.IntegerField(help_text="The id coming from active campaign")
    subscribers = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    
class Contact(models.Model):
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150, null=True, default=None)
    email = models.CharField(max_length=150, unique=True)
    phone = PhoneNumberField(blank=True, null=True, default=None)

    language = models.CharField(max_length=2)
    country = models.CharField(max_length=30)
    city = models.CharField(max_length=30)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.first_name + " " + self.last_name

PENDING = 'PENDING'
PERSISTED = 'PERSISTED'
STORAGE_SATUS = (
    (PENDING, 'Pending'),
    (PERSISTED, 'Persisted'),
)

LEAD_TYPE = (
    (STRONG, 'Strong'),
    (SOFT, 'Soft'),
    (DISCOVERY, 'Discovery'),
)
# Create your models here.
class FormEntry(models.Model):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, null=True, default=None)

    first_name = models.CharField(max_length=150, default='')
    last_name = models.CharField(max_length=150, default='')
    email = models.CharField(max_length=150)
    phone = PhoneNumberField(blank=True, null=True, default=None)

    course = models.CharField(max_length=30, null=True, default=None)
    client_comments = models.CharField(max_length=250, blank=True, null=True, default=None)
    location = models.CharField(max_length=20, blank=True, null=True, default=None)
    language = models.CharField(max_length=2)
    utm_url = models.CharField(max_length=250)
    utm_medium = models.CharField(max_length=50, blank=True, null=True, default=None)
    utm_campaign = models.CharField(max_length=50, blank=True, null=True, default=None)
    referral_key = models.CharField(max_length=50, blank=True, null=True, default=None)
    tags = models.CharField(max_length=100, blank=True, default='')

    street_address = models.CharField(max_length=250, null=True, default=None)
    country = models.CharField(max_length=30)
    city = models.CharField(max_length=30)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, default=None)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, default=None)
    state = models.CharField(max_length=30, null=True, default=None)
    zip_code = models.IntegerField(null=True, default=None)

    # is it saved into active campaign?
    storage_status = models.CharField(max_length=15, choices=STORAGE_SATUS, default=PENDING)
    lead_type = models.CharField(max_length=15, choices=LEAD_TYPE, null=True, default=None)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.first_name + " " + self.last_name

