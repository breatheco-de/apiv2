import secrets
from django.db import models
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from breathecode.admissions.models import Academy, Cohort
from django.core.validators import RegexValidator

__all__ = [
    'ActiveCampaignAcademy', 'AcademyAlias', 'Automation', 'Tag', 'Contact', 'FormEntry', 'ShortLink',
    'ActiveCampaignWebhook'
]


class AcademyProxy(Academy):

    class Meta:
        proxy = True


INCOMPLETED = 'INCOMPLETED'
COMPLETED = 'COMPLETED'
SYNC_STATUS = (
    (INCOMPLETED, 'Incompleted'),
    (COMPLETED, 'Completed'),
)


class ActiveCampaignAcademy(models.Model):
    ac_key = models.CharField(max_length=150)
    ac_url = models.URLField()
    event_attendancy_automation = models.ForeignKey('Automation',
                                                    on_delete=models.CASCADE,
                                                    blank=True,
                                                    null=True,
                                                    default=None)

    academy = models.OneToOneField(Academy, on_delete=models.CASCADE)

    duplicate_leads_delta_avoidance = models.DurationField(
        default=timedelta(minutes=30),
        help_text='Leads that apply to the same course on this timedelta will not be sent to AC')

    sync_status = models.CharField(
        max_length=15,
        choices=SYNC_STATUS,
        default=INCOMPLETED,
        help_text='Automatically set when interacting with the Active Campaign API')
    sync_message = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default=None,
        help_text='Contains any success or error messages depending on the status')
    last_interaction_at = models.DateTimeField(default=None, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.academy.name}'


class AcademyAlias(models.Model):
    """
    The academy alias is great to accept several utm_location or location slug
    for the same academy in active campaign or breathecode when a new lead
    applies to the academy it will look for matching alias to find the lead
    academy.
    """
    slug = models.SlugField(primary_key=True)
    active_campaign_slug = models.SlugField()
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)


ACTIVE = '1'
INNACTIVE = '2'
UKNOWN = '0'
AUTOMATION_STATUS = (
    (ACTIVE, 'Active'),
    (INNACTIVE, 'Innactive'),
    (UKNOWN, 'Uknown'),
)


class Automation(models.Model):
    slug = models.SlugField(
        max_length=150,
        blank=True,
        default='',
        help_text='unique string id that is used to connect incoming leads to automations')
    name = models.CharField(max_length=100)
    acp_id = models.PositiveIntegerField(help_text='ID asigned in active campaign')
    status = models.CharField(max_length=1,
                              choices=AUTOMATION_STATUS,
                              default=UKNOWN,
                              help_text='2 = inactive, 1=active')
    entered = models.PositiveIntegerField(help_text='How many contacts have entered')
    exited = models.PositiveIntegerField(help_text='How many contacts have exited')

    ac_academy = models.ForeignKey(ActiveCampaignAcademy, on_delete=models.CASCADE, null=True, default=None)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        tag_imporance = self.slug if self.slug != '' else 'unknown'
        return f'{tag_imporance} -> {self.name}'


STRONG = 'STRONG'
SOFT = 'SOFT'
DISCOVERY = 'DISCOVERY'
COHORT = 'COHORT'
DOWNLOADABLE = 'DOWNLOADABLE'
EVENT = 'EVENT'
OTHER = 'OTHER'
TAG_TYPE = (
    (STRONG, 'Strong'),
    (SOFT, 'Soft'),
    (DISCOVERY, 'Discovery'),
    (COHORT, 'Cohort'),
    (DOWNLOADABLE, 'Downloadable'),
    (EVENT, 'Event'),
    (OTHER, 'Other'),
)


class Tag(models.Model):
    slug = models.SlugField(max_length=150)
    tag_type = models.CharField(
        max_length=15,
        choices=TAG_TYPE,
        null=True,
        default=None,
        help_text=
        "The STRONG tags in a lead will determine to witch automation it does unless there is an 'automation' property on the lead JSON"
    )
    acp_id = models.IntegerField(help_text='The id coming from active campaign')
    subscribers = models.IntegerField()

    # For better maintance the tags can be disputed for deletion
    disputed_at = models.DateTimeField(
        blank=True,
        null=True,
        default=None,
        help_text=
        'Disputed tags get deleted after 10 days unless its used in 1+ automations or has 1+ subscriber')
    disputed_reason = models.TextField(blank=True,
                                       null=True,
                                       default=None,
                                       help_text='Explain why you think the tag should be deleted')
    description = models.TextField(blank=True,
                                   null=True,
                                   default=None,
                                   help_text='How is this tag being used? Why is it needed?')

    automation = models.ForeignKey(
        Automation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=None,
        help_text='Leads that contain this tag will be asociated to this automation')

    ac_academy = models.ForeignKey(ActiveCampaignAcademy, on_delete=models.CASCADE, null=True, default=None)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.slug} ({str(self.id)})'


class Contact(models.Model):
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150, null=True, default=None)
    email = models.CharField(max_length=150, unique=True)

    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    phone = models.CharField(validators=[phone_regex], max_length=17, blank=True, null=True,
                             default=None)  # validators should be a list

    language = models.CharField(max_length=2)
    country = models.CharField(max_length=30)
    city = models.CharField(max_length=30)

    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.first_name + ' ' + self.last_name


OK = 'OK'
ERROR = 'ERROR'
LAST_CALL_STATUS = (
    (OK, 'Ok'),
    (ERROR, 'Error'),
)


class LeadGenerationApp(models.Model):
    slug = models.SlugField(max_length=150, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=450)
    app_id = models.CharField(
        max_length=255,
        unique=True,
        help_text='Unique token generated only for this app, can be reset to revoke access')

    hits = models.IntegerField(default=0)

    last_request_data = models.TextField(max_length=450,
                                         default=None,
                                         null=True,
                                         blank=True,
                                         help_text='Incomig payload from the last request')

    last_call_status = models.CharField(max_length=9,
                                        choices=LAST_CALL_STATUS,
                                        default=None,
                                        null=True,
                                        blank=True)
    last_call_at = models.DateTimeField(default=None,
                                        blank=True,
                                        null=True,
                                        help_text='Timestamp from the last time this app called our API')

    # defaults
    default_tags = models.ManyToManyField(Tag, blank=True)
    default_automations = models.ManyToManyField(
        Automation,
        blank=True,
        help_text='Automations with are slug will be excluded, make sure to set slug to them')
    location = models.CharField(max_length=70, blank=True, null=True, default=None)
    language = models.CharField(max_length=2, blank=True, null=True, default=None)
    utm_url = models.CharField(max_length=2000, null=True, default=None, blank=True)
    utm_medium = models.CharField(max_length=70, blank=True, null=True, default=None)
    utm_campaign = models.CharField(max_length=70, blank=True, null=True, default=None)
    utm_source = models.CharField(max_length=70, blank=True, null=True, default=None)

    # Status
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.slug}'

    def save(self, *args, **kwargs):
        created = not self.id

        if created:
            self.app_id = secrets.token_urlsafe(16)

        super().save(*args, **kwargs)


PENDING = 'PENDING'
PERSISTED = 'PERSISTED'
DUPLICATED = 'DUPLICATED'
ERROR = 'ERROR'
STORAGE_SATUS = (
    (PENDING, 'Pending'),
    (PERSISTED, 'Persisted'),
    (DUPLICATED, 'Duplicated'),
    (ERROR, 'Error'),
)

LEAD_TYPE = (
    (STRONG, 'Strong'),
    (SOFT, 'Soft'),
    (DISCOVERY, 'Discovery'),
)

WON = 'WON'
LOST = 'LOST'
DEAL_STATUS = (
    (WON, 'Won'),
    (LOST, 'Lost'),
)

GOOD = 'GOOD'
BAD = 'BAD'
DEAL_SENTIMENT = (
    (GOOD, 'Good'),
    (BAD, 'Bad'),
)


# Create your models here.
class FormEntry(models.Model):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, null=True, default=None, blank=True)

    fb_leadgen_id = models.BigIntegerField(null=True, default=None, blank=True)
    fb_page_id = models.BigIntegerField(null=True, default=None, blank=True)
    fb_form_id = models.BigIntegerField(null=True, default=None, blank=True)
    fb_adgroup_id = models.BigIntegerField(null=True, default=None, blank=True)
    fb_ad_id = models.BigIntegerField(null=True, default=None, blank=True)

    ac_contact_id = models.CharField(max_length=20,
                                     null=True,
                                     default=None,
                                     blank=True,
                                     help_text='Active Campaign Contact ID')
    ac_deal_id = models.CharField(max_length=20,
                                  null=True,
                                  default=None,
                                  blank=True,
                                  help_text='Active Campaign Deal ID')

    first_name = models.CharField(max_length=150, default='')
    last_name = models.CharField(max_length=150, default='', blank=True)
    email = models.CharField(max_length=150, null=True, default=None, blank=True)

    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    phone = models.CharField(validators=[phone_regex], max_length=17, blank=True, null=True,
                             default=None)  # validators should be a list

    course = models.CharField(max_length=70, null=True, default=None)
    client_comments = models.CharField(max_length=250, blank=True, null=True, default=None)
    location = models.CharField(max_length=70, blank=True, null=True, default=None)
    language = models.CharField(max_length=2, default='en')
    utm_url = models.CharField(max_length=2000, null=True, default=None, blank=True)
    utm_medium = models.CharField(max_length=70, blank=True, null=True, default=None)
    utm_content = models.CharField(max_length=70, blank=True, null=True, default=None)
    utm_campaign = models.CharField(max_length=70, blank=True, null=True, default=None)
    utm_content = models.CharField(max_length=70, blank=True, null=True, default=None)
    utm_source = models.CharField(max_length=70, blank=True, null=True, default=None)

    current_download = models.CharField(max_length=255,
                                        blank=True,
                                        null=True,
                                        default=None,
                                        help_text='Slug of the breathecode.marketing.downloadable')

    referral_key = models.CharField(max_length=70, blank=True, null=True, default=None)

    gclid = models.CharField(max_length=255, blank=True, null=True, default=None)

    tags = models.CharField(max_length=100, blank=True, default='', help_text='Comma separated list of tags')
    automations = models.CharField(max_length=100,
                                   blank=True,
                                   default='',
                                   help_text='Comma separated list of automations')

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
    storage_status_text = models.CharField(
        default='',
        blank=True,
        max_length=250,
        help_text='Will show exception message or any other cloud on the error that occurred (if any)')

    lead_type = models.CharField(max_length=15, choices=LEAD_TYPE, null=True, default=None)

    deal_status = models.CharField(max_length=15, choices=DEAL_STATUS, default=None, null=True, blank=True)
    sentiment = models.CharField(max_length=15, choices=DEAL_SENTIMENT, default=None, null=True, blank=True)

    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, null=True, default=None)

    lead_generation_app = models.ForeignKey(
        LeadGenerationApp,
        on_delete=models.CASCADE,
        null=True,
        default=None,
        help_text='Other apps can send leads to breathecode but they need to be registered here')

    # if user is not null, it probably means the lead was won and we invited it to breathecode
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, default=None, blank=True)

    ac_expected_cohort = models.CharField(max_length=100,
                                          null=True,
                                          default=None,
                                          blank=True,
                                          help_text='Which cohort is this student expecting to join')
    ac_contact_id = models.CharField(max_length=20,
                                     null=True,
                                     default=None,
                                     blank=True,
                                     help_text='Active Campaign Contact ID')
    ac_deal_id = models.CharField(max_length=20,
                                  null=True,
                                  default=None,
                                  blank=True,
                                  help_text='Active Campaign Deal ID')
    won_at = models.DateTimeField(default=None, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.first_name + ' ' + self.last_name

    def is_duplicate(self, incoming_lead):
        duplicate_leads_delta_avoidance = timedelta(minutes=30)
        if self.academy is not None and self.academy.activecampaignacademy is not None:
            duplicate_leads_delta_avoidance = self.academy.activecampaignacademy.duplicate_leads_delta_avoidance

        last_one = FormEntry.objects.filter(
            email=self.email,
            course=incoming_lead['course'],
            storage_status='PERSISTED',
            created_at__lte=self.created_at).exclude(id=self.id).order_by('-created_at').first()

        if last_one is None:
            return False

        delta = self.created_at - last_one.created_at
        if duplicate_leads_delta_avoidance >= delta:
            return True

        return False

    def toFormData(self):
        _entry = {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'email': self.email,
            'location': self.location,
            'referral_key': self.referral_key,
            'course': self.course,
            'tags': self.tags,
            'automations': self.automations,
            'language': self.language,
            'city': self.city,
            'country': self.country,
            'utm_url': self.utm_url,
            'client_comments': self.client_comments,
            'current_download': self.current_download,
            'latitude': self.longitude,
            'longitude': self.latitude,
        }
        return _entry


_ACTIVE = 'ACTIVE'
NOT_FOUND = 'NOT_FOUND'
DESTINATION_STATUS = (
    (_ACTIVE, 'Active'),
    (NOT_FOUND, 'Not found'),
    (ERROR, 'Error'),
)


class ShortLink(models.Model):
    slug = models.SlugField(max_length=150, unique=True)
    destination = models.URLField()
    hits = models.IntegerField(default=0)
    active = models.BooleanField(default=True)
    private = models.BooleanField(default=True)

    destination_status = models.CharField(max_length=15, choices=DESTINATION_STATUS, default=_ACTIVE)
    destination_status_text = models.CharField(max_length=250, default=None, blank=True, null=True)

    utm_content = models.CharField(max_length=250, null=True, default=None, blank=True)
    utm_medium = models.CharField(max_length=50, blank=True, null=True, default=None)
    utm_campaign = models.CharField(max_length=50, blank=True, null=True, default=None)
    utm_source = models.CharField(max_length=50, blank=True, null=True, default=None)

    # Status
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)

    lastclick_at = models.DateTimeField(blank=True,
                                        null=True,
                                        default=None,
                                        help_text='Last time a click was registered for this link')

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{str(self.hits)} {self.slug}'


PENDING = 'PENDING'
DONE = 'DONE'
WEBHOOK_STATUS = (
    (PENDING, 'Pending'),
    (DONE, 'Done'),
    (ERROR, 'Error'),
)


class ActiveCampaignWebhook(models.Model):

    webhook_type = models.CharField(max_length=100, blank=True, null=True, default=None)
    run_at = models.DateTimeField(help_text='Date/time that the webhook ran')
    initiated_by = models.CharField(
        max_length=100, help_text='Source/section of the software that triggered the webhook to run')

    payload = models.JSONField(
        help_text='Extra info that came on the request, it varies depending on the webhook type')

    ac_academy = models.ForeignKey(ActiveCampaignAcademy, on_delete=models.CASCADE)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, default=None, null=True, blank=True)
    form_entry = models.ForeignKey(FormEntry, on_delete=models.CASCADE, default=None, null=True, blank=True)

    status = models.CharField(max_length=9, choices=WEBHOOK_STATUS, default=PENDING)
    status_text = models.CharField(max_length=255, default=None, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'Webhook {self.webhook_type} {self.status} => {self.status_text}'


class Downloadable(models.Model):
    slug = models.SlugField(max_length=150, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=450)

    hits = models.IntegerField(default=0)
    active = models.BooleanField(default=True,
                                 help_text='Non-active downloadables will display a message to the user')

    preview_url = models.URLField()
    destination_url = models.URLField()
    destination_status = models.CharField(max_length=15, choices=DESTINATION_STATUS, default=_ACTIVE)

    # Status
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.slug}'

    def save(self, *args, **kwargs):
        from .signals import downloadable_saved
        created = not self.id

        if created:
            super().save(*args, **kwargs)

            downloadable_saved.send(instance=self, sender=self.__class__, created=created)


SOURCE = 'SOURCE'
MEDIUM = 'MEDIUM'
CONTENT = 'CONTENT'
CAMPAIGN = 'CAMPAIGN'
UTM_TYPE = (
    (CONTENT, 'Content'),
    (SOURCE, 'Source'),
    (MEDIUM, 'Medium'),
    (CAMPAIGN, 'Campaign'),
)


class UTMField(models.Model):
    slug = models.SlugField(max_length=150, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=450)

    # Status
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)

    utm_type = models.CharField(max_length=15, choices=UTM_TYPE, default=None)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.slug}'
