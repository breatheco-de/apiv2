import string, datetime
from django.db import models
from django.contrib.auth.models import User
from breathecode.admissions.models import Academy
from django.core.validators import RegexValidator

INCOMPLETED = 'INCOMPLETED'
COMPLETED = 'COMPLETED'
SYNC_STATUS = (
    (INCOMPLETED, 'Incompleted'),
    (COMPLETED, 'Completed'),
)
class ActiveCampaignAcademy(models.Model):
    ac_key = models.CharField(max_length=150)
    ac_url = models.CharField(max_length=150)

    academy = models.OneToOneField(Academy, on_delete=models.CASCADE)

    sync_status = models.CharField(max_length=15, choices=SYNC_STATUS, default=INCOMPLETED, help_text="Automatically set when interacting with the Active Campaign API")
    sync_message = models.CharField(max_length=100, blank=True, null=True, default=None, help_text="Contains any success or error messages depending on the status")
    last_interaction_at = models.DateTimeField(default=None, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.academy.name}"

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
    acp_id = models.PositiveIntegerField(help_text="ID asigned in active campaign")
    status = models.CharField(max_length=1, choices=AUTOMATION_STATUS, default=UKNOWN, help_text="2 = inactive, 1=active")
    entered = models.PositiveSmallIntegerField(help_text="How many contacts have entered")
    exited = models.PositiveSmallIntegerField(help_text="How many contacts have exited")

    ac_academy = models.ForeignKey(ActiveCampaignAcademy, on_delete=models.CASCADE, null=True, default=None)

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
    slug = models.SlugField(max_length=150)
    tag_type = models.CharField(max_length=15, choices=TAG_TYPE, null=True, default=None, help_text="The STRONG tags in a lead will determine to witch automation it does unless there is an 'automation' property on the lead JSON")
    acp_id = models.IntegerField(help_text="The id coming from active campaign")
    subscribers = models.IntegerField()
    automation = models.ForeignKey(Automation, on_delete=models.CASCADE, null=True, default=None, help_text="Leads that contain this tag will be asociated to this automation")

    ac_academy = models.ForeignKey(ActiveCampaignAcademy, on_delete=models.CASCADE, null=True, default=None)

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

    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)

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
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, null=True, default=None, blank=True)

    fb_leadgen_id = models.BigIntegerField(null=True, default=None, blank=True)
    fb_page_id = models.BigIntegerField(null=True, default=None, blank=True)
    fb_form_id = models.BigIntegerField(null=True, default=None, blank=True)
    fb_adgroup_id = models.BigIntegerField(null=True, default=None, blank=True)
    fb_ad_id = models.BigIntegerField(null=True, default=None, blank=True)

    first_name = models.CharField(max_length=150, default='')
    last_name = models.CharField(max_length=150, default='')
    email = models.CharField(max_length=150, null=True, default=None, blank=True)

    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    phone = models.CharField(validators=[phone_regex], max_length=17, blank=True, null=True, default=None) # validators should be a list

    course = models.CharField(max_length=30, null=True, default=None)
    client_comments = models.CharField(max_length=250, blank=True, null=True, default=None)
    location = models.CharField(max_length=20, blank=True, null=True, default=None)
    language = models.CharField(max_length=2, default='en')
    utm_url = models.CharField(max_length=250, null=True, default=None, blank=True)
    utm_medium = models.CharField(max_length=50, blank=True, null=True, default=None)
    utm_campaign = models.CharField(max_length=50, blank=True, null=True, default=None)
    utm_source = models.CharField(max_length=50, blank=True, null=True, default=None)
    referral_key = models.CharField(max_length=50, blank=True, null=True, default=None)
    
    gclid = models.CharField(max_length=255, blank=True, null=True, default=None)
    
    tags = models.CharField(max_length=100, blank=True, default='')
    automations = models.CharField(max_length=100, blank=True, default='')

    tag_objects = models.ManyToManyField(Tag, blank=True)
    automation_objects = models.ManyToManyField(Automation, blank=True)

    street_address = models.CharField(max_length=250, null=True, default=None, blank=True)
    country = models.CharField(max_length=30, null=True, default=None, blank=True)
    city = models.CharField(max_length=30, null=True, default=None, blank=True)
    latitude = models.DecimalField(max_digits=30, decimal_places=15, null=True, default=None, blank=True)
    longitude = models.DecimalField(max_digits=30, decimal_places=15, null=True, default=None, blank=True)
    state = models.CharField(max_length=30, null=True, default=None, blank=True)
    zip_code = models.IntegerField(null=True, default=None, blank=True)
    browser_lang = models.CharField(max_length=10, null=True, default=None, blank=True)

    # is it saved into active campaign?
    storage_status = models.CharField(max_length=15, choices=STORAGE_SATUS, default=PENDING)
    lead_type = models.CharField(max_length=15, choices=LEAD_TYPE, null=True, default=None)

    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, null=True, default=None)
    ac_academy = models.ForeignKey(ActiveCampaignAcademy, on_delete=models.CASCADE, null=True, default=None)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.first_name + " " + self.last_name

    def toFormData(self):
        _entry = {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone": self.phone,
            "email": self.email,
            "location": self.location,
            "referral_key": self.referral_key,
            "course": self.course,
            "tags": self.tags,
            "automations": self.automations,
            "language": self.language,
            "city": self.city,
            "country": self.country,
            "utm_url": self.utm_url,
            "client_comments": self.client_comments,
            "latitude": self.longitude,
            "longitude": self.latitude,
        }
        return _entry

_ACTIVE = 'ACTIVE'
NOT_FOUND = 'NOT_FOUND'
DESTINATION_STATUS = (
    (_ACTIVE, 'Active'),
    (NOT_FOUND, 'Not found'),
)
class ShortLink(models.Model):
    slug = models.SlugField(max_length=150, unique=True)
    destination = models.URLField()
    hits = models.IntegerField(default=0)
    active = models.BooleanField(default=True)
    destination_status = models.CharField(max_length=15, choices=DESTINATION_STATUS, default=_ACTIVE)

    utm_content = models.CharField(max_length=250, null=True, default=None, blank=True)
    utm_medium = models.CharField(max_length=50, blank=True, null=True, default=None)
    utm_campaign = models.CharField(max_length=50, blank=True, null=True, default=None)
    utm_source = models.CharField(max_length=50, blank=True, null=True, default=None)

    # Status
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{str(self.hits)} {self.slug}"