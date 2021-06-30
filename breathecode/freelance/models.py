from django.contrib.auth.models import User
from django.db import models
from breathecode.authenticate.models import CredentialsGithub
from breathecode.admissions.models import Academy


class Freelancer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    github_user = models.ForeignKey(CredentialsGithub,
                                    on_delete=models.SET_DEFAULT,
                                    null=True,
                                    default=None)
    price_per_hour = models.FloatField()

    def __str__(self):
        return self.user.email


DUE = 'DUE'
APPROVED = 'APPROVED'
PAID = 'PAID'
BILL_STATUS = (
    (DUE, 'Due'),
    (APPROVED, 'Approved'),
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
                                default=None)

    reviewer = models.ForeignKey(User,
                                 on_delete=models.CASCADE,
                                 null=True,
                                 default=None)
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

    status = models.CharField(max_length=20,
                              choices=ISSUE_STATUS,
                              default=DRAFT)
    github_state = models.CharField(max_length=30,
                                    blank=True,
                                    null=True,
                                    default=None)
    github_number = models.PositiveIntegerField()
    body = models.TextField(max_length=500)

    duration_in_minutes = models.FloatField(default=0)
    duration_in_hours = models.FloatField(default=0)

    url = models.URLField(max_length=255)
    repository_url = models.URLField(max_length=255,
                                     blank=True,
                                     default=None,
                                     null=True)

    author = models.ForeignKey(User,
                               on_delete=models.CASCADE,
                               null=True,
                               default=None,
                               blank=True)
    freelancer = models.ForeignKey(Freelancer, on_delete=models.CASCADE)
    bill = models.ForeignKey(Bill,
                             on_delete=models.CASCADE,
                             null=True,
                             default=None,
                             blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
