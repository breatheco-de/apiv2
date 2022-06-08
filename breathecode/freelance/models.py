from django.contrib.auth.models import User
from django.db import models
from breathecode.authenticate.models import CredentialsGithub
from breathecode.admissions.models import Academy

__all__ = ['Freelancer', 'Bill', 'Issue']


class Freelancer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    github_user = models.ForeignKey(CredentialsGithub, on_delete=models.SET_DEFAULT, null=True, default=None)
    price_per_hour = models.FloatField()

    def __str__(self):
        return self.user.email


DUE = 'DUE'
APPROVED = 'APPROVED'
PAID = 'PAID'
IGNORED = 'IGNORED'
BILL_STATUS = (
    (DUE, 'Due'),
    (APPROVED, 'Approved'),
    (IGNORED, 'Ignored'),
    (PAID, 'Paid'),
)


class Bill(models.Model):
    status = models.CharField(max_length=20, choices=BILL_STATUS, default=DUE)

    total_duration_in_minutes = models.FloatField(default=0)
    total_duration_in_hours = models.FloatField(default=0)
    total_price = models.FloatField(default=0)

    academy = models.ForeignKey(Academy,
                                on_delete=models.CASCADE,
                                null=True,
                                default=None,
                                blank=True,
                                help_text='Will help catalog billing grouped by academy')

    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, null=True, default=None)
    freelancer = models.ForeignKey(Freelancer, on_delete=models.CASCADE)
    paid_at = models.DateTimeField(null=True, default=None, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


IGNORED = 'IGNORED'
DRAFT = 'DRAFT'
TODO = 'TODO'
DOING = 'DOING'
DONE = 'DONE'
ISSUE_STATUS = (
    (IGNORED, 'Ignored'),
    (DRAFT, 'Draft'),
    (TODO, 'Todo'),
    (DOING, 'Doing'),
    (DONE, 'Done'),
)


class Issue(models.Model):
    title = models.CharField(max_length=255)

    node_id = models.CharField(
        max_length=50,
        default=None,
        null=True,
        blank=True,
        help_text=
        'This is the only unique identifier we get from github, the issue number its not unique among repos')
    status = models.CharField(max_length=20, choices=ISSUE_STATUS, default=DRAFT)
    status_message = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        default=None,
        help_text='Important message like reasong why not included on bill, etc.')

    github_state = models.CharField(max_length=30, blank=True, null=True, default=None)
    github_number = models.PositiveIntegerField()
    body = models.TextField(max_length=500)

    duration_in_minutes = models.FloatField(default=0)
    duration_in_hours = models.FloatField(default=0)

    url = models.URLField()
    repository_url = models.URLField(blank=True, default=None, null=True)

    author = models.ForeignKey(User, on_delete=models.CASCADE, null=True, default=None, blank=True)
    freelancer = models.ForeignKey(Freelancer, on_delete=models.CASCADE)

    academy = models.ForeignKey(Academy,
                                on_delete=models.CASCADE,
                                null=True,
                                default=None,
                                blank=True,
                                help_text='Will help catalog billing grouped by academy')
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, null=True, default=None, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


PENDING = 'PENDING'
DONE = 'DONE'
ERROR = 'ERROR'
WEBHOOK_STATUS = (
    (PENDING, 'Pending'),
    (DONE, 'Done'),
    (ERROR, 'Error'),
)


class RepositoryIssueWebhook(models.Model):

    webhook_action = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default=None,
        help_text='The specific action that was triggered on github for this webhook')
    run_at = models.DateTimeField(help_text='Date/time that the webhook ran',
                                  blank=True,
                                  null=True,
                                  default=None)
    repository = models.URLField(max_length=255, help_text='Github repo where the event occured')

    payload = models.JSONField(
        help_text='Info that came on the request, it varies depending on the webhook type')

    academy_slug = models.SlugField()

    status = models.CharField(max_length=9, choices=WEBHOOK_STATUS, default=PENDING)
    status_text = models.CharField(max_length=255, default=None, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'Webhook {self.webhook_action} {self.status} => {self.status_text}'
