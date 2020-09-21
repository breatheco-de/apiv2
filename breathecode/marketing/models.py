from django.db import models
from django.core.validators import RegexValidator

ACTIVE = '1'
INNACTIVE = '2'
UKNOWN = '0'
AUTOMATION_STATUS = (
    (ACTIVE, 'Active'),
    (INNACTIVE, 'Innactive'),
    (UKNOWN, 'Uknown'),
)
class Automation(models.Model):
    slug = models.SlugField(max_length=150, blank=True, default='', help_text="unique string id that is used to connect incoming leads to automations")
    name = models.CharField(max_length=100)
    acp_id = models.PositiveSmallIntegerField(unique=True, help_text="ID asigned in active campaign")
    status = models.CharField(max_length=1, choices=AUTOMATION_STATUS, default=UKNOWN, help_text="2 = inactive, 1=active")
    entered = models.PositiveSmallIntegerField(help_text="How many contacts have entered")
    exited = models.PositiveSmallIntegerField(help_text="How many contacts have exited")

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        tag_imporance = self.slug if self.slug != '' else "unknown"
        return f"{tag_imporance} -> {self.name}"

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
    slug = models.SlugField(max_length=150, unique=True)
    tag_type = models.CharField(max_length=15, choices=TAG_TYPE, null=True, default=None, help_text="The STRONG tags in a lead will determine to witch automation it does unless there is an 'automation' property on the lead JSON")
    acp_id = models.IntegerField(unique=True, help_text="The id coming from active campaign")
    subscribers = models.IntegerField()
    automation = models.ForeignKey(Automation, on_delete=models.CASCADE, null=True, default=None, help_text="Leads that contain this tag will be asociated to this automation")

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.slug} ({str(self.id)})'
    
class Contact(models.Model):
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150, null=True, default=None)
    email = models.CharField(max_length=150, unique=True)

    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    phone = models.CharField(validators=[phone_regex], max_length=17, blank=True, null=True, default=None) # validators should be a list

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

    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    phone = models.CharField(validators=[phone_regex], max_length=17, blank=True, null=True, default=None) # validators should be a list

    course = models.CharField(max_length=30, null=True, default=None)
    client_comments = models.CharField(max_length=250, blank=True, null=True, default=None)
    location = models.CharField(max_length=20, blank=True, null=True, default=None)
    language = models.CharField(max_length=2)
    utm_url = models.CharField(max_length=250)
    utm_medium = models.CharField(max_length=50, blank=True, null=True, default=None)
    utm_campaign = models.CharField(max_length=50, blank=True, null=True, default=None)
    referral_key = models.CharField(max_length=50, blank=True, null=True, default=None)
    
    tags = models.CharField(max_length=100, blank=True, default='')
    automations = models.CharField(max_length=100, blank=True, default='')

    tag_objects = models.ManyToManyField(Tag, blank=True)
    automation_objects = models.ManyToManyField(Automation, blank=True)

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

