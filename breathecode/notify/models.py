from django.db import models
from django.contrib.auth.models import User
from breathecode.admissions.models import Academy, Cohort
from breathecode.authenticate.models import CredentialsSlack


class UserProxy(User):
    class Meta:
        proxy = True


class CohortProxy(Cohort):
    class Meta:
        proxy = True


class Device(models.Model):
    user = models.ForeignKey(User,
                             on_delete=models.CASCADE,
                             blank=True,
                             null=True)
    registration_id = models.TextField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.user.registration_id


INCOMPLETED = 'INCOMPLETED'
COMPLETED = 'COMPLETED'
SYNC_STATUS = (
    (INCOMPLETED, 'Incompleted'),
    (COMPLETED, 'Completed'),
)


class SlackTeam(models.Model):

    slack_id = models.CharField(max_length=50)
    name = models.CharField(max_length=100)

    # the owner represents the channel
    # his/her credentials are used for interaction with the Slack API
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    academy = models.OneToOneField(Academy,
                                   on_delete=models.CASCADE,
                                   blank=True)

    sync_status = models.CharField(
        max_length=15,
        choices=SYNC_STATUS,
        default=INCOMPLETED,
        help_text="Automatically set when synqued from slack")
    sync_message = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default=None,
        help_text=
        "Contains any success or error messages depending on the status")
    synqued_at = models.DateTimeField(default=None, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.name} ({self.slack_id})"


class SlackUser(models.Model):
    user = models.OneToOneField(User,
                                on_delete=models.CASCADE,
                                blank=True,
                                null=True,
                                default=None)

    slack_id = models.CharField(max_length=50)
    status_text = models.CharField(max_length=255, blank=True, null=True)
    status_emoji = models.CharField(max_length=100, blank=True, null=True)
    real_name = models.CharField(max_length=100, blank=True, null=True)
    display_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.slack_id


class SlackUserTeam(models.Model):
    slack_user = models.ForeignKey(SlackUser, on_delete=models.CASCADE)
    slack_team = models.ForeignKey(SlackTeam, on_delete=models.CASCADE)

    sync_status = models.CharField(max_length=15,
                                   choices=SYNC_STATUS,
                                   default=INCOMPLETED)
    sync_message = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default=None,
        help_text=
        "Contains any success or error messages depending on the status")
    synqued_at = models.DateTimeField(default=None, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


class SlackChannel(models.Model):
    cohort = models.OneToOneField(Cohort,
                                  on_delete=models.CASCADE,
                                  blank=True,
                                  null=True,
                                  default=None)
    # academy = models.OneToOneField(Academy, on_delete=models.CASCADE, blank=True, null=True, default=None)

    slack_id = models.CharField(max_length=50)
    team = models.ForeignKey(SlackTeam, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, blank=True, null=True)

    topic = models.CharField(max_length=500, blank=True, null=True)
    purpose = models.CharField(max_length=500, blank=True, null=True)

    sync_status = models.CharField(max_length=15,
                                   choices=SYNC_STATUS,
                                   default=INCOMPLETED)
    sync_message = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default=None,
        help_text=
        "Contains any success or error messages depending on the status")
    synqued_at = models.DateTimeField(default=None, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        name = self.name if self.name else 'Unknown'
        return f'{name}({self.slack_id})'
