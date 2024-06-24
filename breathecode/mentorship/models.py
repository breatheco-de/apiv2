import binascii
import hashlib
import os
from datetime import timedelta

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

import breathecode.mentorship.signals as signals
from breathecode.admissions.models import Academy, Syllabus
from breathecode.notify.models import SlackChannel
from breathecode.utils.validators.language import validate_language_code


class VideoProvider(models.TextChoices):
    DAILY = ('DAILY', 'Daily')
    GOOGLE_MEET = ('GOOGLE_MEET', 'Google Meet')


MENTORSHIP_SETTINGS = {
    'duration': timedelta(hours=1),
    'max_duration': timedelta(hours=2),
    'missed_meeting_duration': timedelta(minutes=10),
    'language': 'en',
    'allow_mentee_to_extend': True,
    'allow_mentors_to_extend': True,
    'video_provider': VideoProvider.GOOGLE_MEET,
}


class AcademyMentorshipSettings(models.Model):
    VideoProvider = VideoProvider

    academy = models.OneToOneField(Academy, on_delete=models.CASCADE)
    duration = models.DurationField(default=MENTORSHIP_SETTINGS['duration'],
                                    help_text='Default duration for mentorship sessions of this service')

    max_duration = models.DurationField(
        default=MENTORSHIP_SETTINGS['max_duration'],
        help_text='Maximum allowed duration or extra time, make it 0 for unlimited meetings')

    missed_meeting_duration = models.DurationField(
        default=MENTORSHIP_SETTINGS['missed_meeting_duration'],
        help_text='Duration that will be paid when the mentee doesn\'t come to the session')

    language = models.CharField(max_length=5,
                                default=MENTORSHIP_SETTINGS['language'],
                                validators=[validate_language_code],
                                help_text='ISO 639-1 language code + ISO 3166-1 alpha-2 country code, e.g. en-US')

    allow_mentee_to_extend = models.BooleanField(default=MENTORSHIP_SETTINGS['allow_mentee_to_extend'],
                                                 help_text='If true, mentees will be able to extend mentorship session')
    allow_mentors_to_extend = models.BooleanField(
        default=MENTORSHIP_SETTINGS['allow_mentors_to_extend'],
        help_text='If true, mentors will be able to extend mentorship session')

    video_provider = models.CharField(max_length=15, choices=VideoProvider, default=VideoProvider.GOOGLE_MEET)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.academy.name

    def clean(self) -> None:
        return super().clean()

    def save(self, **kwargs) -> None:
        return super().save(**kwargs)


class MentorshipService(models.Model):
    VideoProvider = VideoProvider

    class Status(models.TextChoices):
        DRAFT = ('DRAFT', 'Draft')
        ACTIVE = ('ACTIVE', 'Active')
        UNLISTED = ('UNLISTED', 'Unlisted')
        INNACTIVE = ('INNACTIVE', 'Innactive')

    slug = models.SlugField(max_length=150, unique=True)
    name = models.CharField(max_length=150)
    logo_url = models.CharField(max_length=150, default=None, blank=True, null=True)
    description = models.TextField(max_length=500, default=None, blank=True, null=True)

    duration = models.DurationField(default=None,
                                    blank=True,
                                    help_text='Default duration for mentorship sessions of this service')

    max_duration = models.DurationField(
        default=None, blank=True, help_text='Maximum allowed duration or extra time, make it 0 for unlimited meetings')

    missed_meeting_duration = models.DurationField(
        default=None, blank=True, help_text='Duration that will be paid when the mentee doesn\'t come to the session')

    status = models.CharField(max_length=15, choices=Status, default=Status.DRAFT)

    language = models.CharField(max_length=5,
                                default=None,
                                blank=True,
                                validators=[validate_language_code],
                                help_text='ISO 639-1 language code + ISO 3166-1 alpha-2 country code, e.g. en-US')

    allow_mentee_to_extend = models.BooleanField(blank=True,
                                                 default=None,
                                                 help_text='If true, mentees will be able to extend mentorship session')
    allow_mentors_to_extend = models.BooleanField(
        default=None, blank=True, help_text='If true, mentors will be able to extend mentorship session')

    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    video_provider = models.CharField(max_length=15, default=None, choices=VideoProvider, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.name} ({self.slug})'

    def clean(self) -> None:
        fetched = False
        academy_settings = None
        for field, value in MENTORSHIP_SETTINGS.items():
            current = getattr(self, field)
            if current is None:
                if fetched is False:
                    fetched = True
                    academy_settings = AcademyMentorshipSettings.objects.filter(academy=self.academy).first()

                if academy_settings:
                    academy_value = getattr(academy_settings, field)
                    setattr(self, field, academy_value)

                else:
                    setattr(self, field, value)

        return super().clean()

    def save(self, **kwargs) -> None:
        self.full_clean()
        return super().save(**kwargs)


class SupportChannel(models.Model):
    slug = models.SlugField(max_length=150)
    slack_channel = models.ForeignKey(SlackChannel, on_delete=models.CASCADE, blank=True, default=None, null=True)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    syllabis = models.ManyToManyField(Syllabus, related_name='support_channels')

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


class MentorStatus(models.TextChoices):
    INVITED = ('INVITED', 'Invited')
    ACTIVE = ('ACTIVE', 'Active')
    UNLISTED = ('UNLISTED', 'Unlisted')
    INNACTIVE = ('INNACTIVE', 'Innactive')


class SupportAgent(models.Model):

    user = models.ForeignKey(User,
                             on_delete=models.CASCADE,
                             help_text='If the user does not exist, you can use the email field instead')
    token = models.CharField(max_length=255,
                             unique=True,
                             help_text='Used for inviting the user to become a support agent')
    status = models.CharField(max_length=15,
                              choices=MentorStatus,
                              default=MentorStatus.INVITED,
                              help_text=f'Options are: {", ".join([key for key,label in MentorStatus.choices])}')

    email = models.CharField(blank=True,
                             max_length=150,
                             null=True,
                             default=None,
                             help_text='Only use this if the user does not exist on 4geeks already')
    one_line_bio = models.TextField(max_length=60, default=None, blank=True, null=True)

    channel = models.ForeignKey(SupportChannel, related_name='agents', on_delete=models.SET_NULL, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def save(self, *args, **kwargs):
        if not self.pk:
            self.token = binascii.hexlify(os.urandom(20)).decode()

        return super().save(*args, **kwargs)


class MentorProfile(models.Model):
    name = models.CharField(max_length=150, blank=True, null=True, default=None)
    slug = models.SlugField(
        max_length=150,
        unique=True,
        help_text='Will be used as unique public booking URL with the students, for example: 4geeks.com/meet/bob')

    price_per_hour = models.FloatField()

    one_line_bio = models.TextField(max_length=60,
                                    default=None,
                                    blank=True,
                                    null=True,
                                    help_text='Will be shown to showcase the mentor')
    bio = models.TextField(max_length=500, default=None, blank=True, null=True)

    services = models.ManyToManyField(to=MentorshipService)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, null=True, default=None)

    timezone = models.CharField(max_length=50,
                                null=True,
                                default=None,
                                help_text='Knowing the mentor\'s timezone helps with more accurrate booking')

    online_meeting_url = models.URLField(
        blank=True,
        null=True,
        default=None,
        help_text="If set, it will be default for all session's unless the session.online_meeting_url is set")

    token = models.CharField(max_length=255, unique=True, help_text='Used for inviting the user to become a mentor')

    booking_url = models.URLField(
        blank=True,
        null=True,
        default=None,
        help_text='URL where this mentor profile can be booked, E.g: calendly.com/my_username')

    syllabus = models.ManyToManyField(to=Syllabus,
                                      blank=True,
                                      default=None,
                                      help_text='What syllabis is this mentor going to be menting to?')

    status = models.CharField(max_length=15,
                              choices=MentorStatus,
                              default=MentorStatus.INVITED,
                              help_text=f'Options are: {", ".join([key for key,label in MentorStatus.choices])}')

    email = models.CharField(blank=True,
                             max_length=150,
                             null=True,
                             default=None,
                             help_text='Only use this if the user does not exist on breathecode already')

    availability_report = models.JSONField(blank=True, null=False, default=[], help_text='Mentor availability report')

    user = models.ForeignKey(User,
                             on_delete=models.CASCADE,
                             help_text='If the user does not exist, you can use the email field instead')

    calendly_uuid = models.CharField(blank=True,
                                     max_length=255,
                                     null=True,
                                     default=None,
                                     help_text='To be used by the calendly API')

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    rating = models.FloatField(
        null=True,
        blank=True,
        default=None,
        help_text='Automatically filled when new survey responses are collected about this mentor')

    def save(self, *args, **kwargs):

        utc_now = timezone.now()
        if self.token is None or self.token == '':
            self.token = hashlib.sha1((str(self.user.id) + str(utc_now)).encode('UTF-8')).hexdigest()

        super().save(*args, **kwargs)  # Call the "real" save() method.

    def __str__(self):
        name = self.name
        if self.user is not None and self.user.first_name is not None and self.user.first_name != '':
            name = self.user.first_name + ' ' + self.user.last_name

        return f'{name} ({self.id})'


RECALCULATE = 'RECALCULATE'
DUE = 'DUE'
APPROVED = 'APPROVED'
PAID = 'PAID'
IGNORED = 'IGNORED'
BILL_STATUS = (
    (RECALCULATE, 'Recalculate'),
    (DUE, 'Due'),
    (APPROVED, 'Approved'),
    (PAID, 'Paid'),
    (IGNORED, 'Ignored'),
)


class MentorshipBill(models.Model):

    status = models.CharField(max_length=20, choices=BILL_STATUS, default=DUE)
    #FIXME: it's right?
    status_mesage = models.TextField(blank=True,
                                     null=True,
                                     default=None,
                                     help_text='Any important information about the bill')

    total_duration_in_minutes = models.FloatField(default=0)
    total_duration_in_hours = models.FloatField(default=0)
    total_price = models.FloatField(default=0)
    overtime_minutes = models.FloatField(
        default=0, help_text='Additional time mentorships took based on the expected default duration')

    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, null=True, default=None)

    started_at = models.DateTimeField(blank=True,
                                      null=True,
                                      default=None,
                                      help_text='The bill includes all sessions from started_at to ended_at')
    ended_at = models.DateTimeField(blank=True,
                                    null=True,
                                    default=None,
                                    help_text='The bill includes all sessions from started_at to ended_at')

    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, null=True, default=None)
    mentor = models.ForeignKey(MentorProfile, on_delete=models.CASCADE)
    paid_at = models.DateTimeField(null=True, default=None, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


PENDING = 'PENDING'
STARTED = 'STARTED'
COMPLETED = 'COMPLETED'
FAILED = 'FAILED'
IGNORED = 'IGNORED'
CANCELED = 'CANCELED'
MENTORSHIP_STATUS = (
    (PENDING, 'Pending'),
    (STARTED, 'Started'),
    (COMPLETED, 'Completed'),
    (CANCELED, 'Canceled'),
    (FAILED, 'Failed'),
    (IGNORED, 'Ignored'),  # will not be included on the bills
)


class MentorshipSession(models.Model):

    def __init__(self, *args, **kwargs):
        super(MentorshipSession, self).__init__(*args, **kwargs)
        self.__old_status = self.status

    name = models.CharField(max_length=255,
                            help_text='Room name, used on daily.co',
                            blank=True,
                            null=True,
                            default=None)

    is_online = models.BooleanField(default=False)
    latitude = models.FloatField(blank=True, null=True, default=None)
    longitude = models.FloatField(blank=True, null=True, default=None)

    mentor = models.ForeignKey(MentorProfile, on_delete=models.CASCADE)
    service = models.ForeignKey(MentorshipService, on_delete=models.CASCADE, blank=True, null=True)
    mentee = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, default=None)

    online_meeting_url = models.URLField(blank=True,
                                         null=True,
                                         default=None,
                                         help_text='Overrides the mentor.online_meeting_url if set')
    online_recording_url = models.URLField(
        blank=True,
        null=True,
        default=None,
        help_text='We encourace the mentors to record the session and share them with the students')

    status = models.CharField(
        max_length=15,
        choices=MENTORSHIP_STATUS,
        default=PENDING,
        help_text=
        f'Options are: {", ".join([key for key,label in MENTORSHIP_STATUS])}. Ignored sessions will not be billed.')
    status_message = models.TextField(default=None, null=True, blank=True)
    allow_billing = models.BooleanField(default=True,
                                        help_text='If false it will not be included when generating mentorship bills')
    bill = models.ForeignKey(MentorshipBill,
                             on_delete=models.SET_NULL,
                             null=True,
                             default=None,
                             blank=True,
                             help_text='If null, it has not been billed by the mentor yet')

    suggested_accounted_duration = models.DurationField(
        blank=True,
        null=True,
        default=None,
        help_text='The automatic suggested duration to be paid to the mentor for this session')

    accounted_duration = models.DurationField(blank=True,
                                              null=True,
                                              default=None,
                                              help_text='The duration that will be paid to the mentor for this session')

    agenda = models.TextField(blank=True, null=True, default=None, help_text='What will this mentorship be about')
    summary = models.TextField(blank=True,
                               null=True,
                               default=None,
                               help_text='Describe briefly what happened at the mentorship session')

    starts_at = models.DateTimeField(blank=True, null=True, default=None, help_text='Scheduled start date')
    ends_at = models.DateTimeField(blank=True,
                                   null=True,
                                   default=None,
                                   help_text='Scheduled end date, will be used as meeting expiration as well')

    started_at = models.DateTimeField(blank=True,
                                      null=True,
                                      default=None,
                                      help_text='Real start date (only if it started)')
    ended_at = models.DateTimeField(blank=True,
                                    null=True,
                                    default=None,
                                    help_text='Real start date (only if it started)')

    mentor_joined_at = models.DateTimeField(blank=True,
                                            null=True,
                                            default=None,
                                            help_text='Exact moment the mentor joined the meeting for the first time')

    mentor_left_at = models.DateTimeField(blank=True,
                                          null=True,
                                          default=None,
                                          help_text='Exact moment the mentor left the meeting for the last time')

    mentee_left_at = models.DateTimeField(blank=True,
                                          null=True,
                                          default=None,
                                          help_text='Exact moment the mentee left the meeting for the last time')

    calendly_uuid = models.CharField(blank=True,
                                     max_length=255,
                                     null=True,
                                     default=None,
                                     help_text='To be used by the calendly API')

    questions_and_answers = models.JSONField(null=True, blank=True, default=None)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'(Session {self.id} with {str(self.mentor)} and {str(self.mentee)})'

    def save(self, *args, **kwargs):

        is_creating = self.pk is None

        super().save(*args, **kwargs)  # Call the "real" save() method.

        if is_creating or self.__old_status != self.status:
            signals.mentorship_session_status.send_robust(instance=self, sender=MentorshipSession)

        self.__old_status = self.status


class ChatBot(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)

    syllabus = models.ManyToManyField(Syllabus, blank=True)

    description = models.TextField(blank=True, null=True, default=None)

    api_key = models.CharField(max_length=250, blank=True)
    api_organization = models.CharField(max_length=250, blank=True)

    def __str__(self):
        return self.name


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


class CalendlyOrganization(models.Model):
    username = models.CharField(max_length=100, help_text='Calendly username')
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, blank=True, null=True)
    access_token = models.TextField(blank=True, null=True, default=None)

    uri = models.URLField(help_text='Automatically collected from calendly API')
    max_concurrent_sessions = models.IntegerField(
        default=None,
        blank=True,
        null=True,
        help_text=
        'For example: Users will only be allowed to book 2 sessions per service at a time, they will have to wait for sessions to complete (or cancel) before booking again'
    )

    # this should be use in the future to create automatically the permalinks
    hash = models.CharField(max_length=40, unique=True)

    sync_status = models.CharField(
        max_length=9,
        choices=SYNC_STATUS,
        default=PENDING,
        help_text='One of: PENDING, PERSISTED or ERROR depending on how the calendly sync status')
    sync_desc = models.TextField(max_length=255, null=True, default=None, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.username or 'Nameless calendly org'

    def save(self, *args, **kwargs):
        if not self.pk:
            self.hash = binascii.hexlify(os.urandom(20)).decode()

        return super().save(*args, **kwargs)

    def reset_hash(self):
        self.hash = binascii.hexlify(os.urandom(20)).decode()
        return self.save()


# PENDING = 'PENDING'
DONE = 'DONE'
WEBHOOK_STATUS = (
    (PENDING, 'Pending'),
    (DONE, 'Done'),
    (ERROR, 'Error'),
)


class CalendlyWebhook(models.Model):
    organization_hash = models.CharField(max_length=50)
    created_by = models.CharField(max_length=2500)
    event = models.CharField(max_length=100)
    called_at = models.DateTimeField()
    payload = models.JSONField()

    organization = models.ForeignKey(CalendlyOrganization,
                                     on_delete=models.CASCADE,
                                     null=True,
                                     default=None,
                                     blank=True)

    status = models.CharField(max_length=9, choices=WEBHOOK_STATUS, default=PENDING)
    status_text = models.TextField(default=None, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'Event {self.event} {self.status} => {self.created_by}'
