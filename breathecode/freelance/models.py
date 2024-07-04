from django.contrib.auth.models import User
from django.db import models
from breathecode.authenticate.models import CredentialsGithub
from breathecode.admissions.models import Academy

__all__ = ["Freelancer", "Bill", "Issue"]


class Freelancer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    github_user = models.ForeignKey(CredentialsGithub, on_delete=models.SET_DEFAULT, null=True, default=None)
    price_per_hour = models.FloatField()

    def __str__(self):
        return self.user.email

    # price paid to the freelancer
    def get_hourly_rate(self, project=None):
        if project is None:
            return self.price_per_hour
        else:
            member = FreelanceProjectMember.objects.filter(project__id=project.id, freelancer__id=self.id).first()
            if member is None:
                return 0
            elif member.total_cost_hourly_price is None:
                return self.price_per_hour
            else:
                return member.total_cost_hourly_price

    # price to charge the client
    def get_client_hourly_rate(self, project):
        member = FreelanceProjectMember.objects.filter(project__id=project.id, freelancer__id=self.id).first()
        if member is None:
            return 0
        elif member.total_client_hourly_price is None:
            return project.total_client_hourly_price
        else:
            return member.total_client_hourly_price


class AcademyFreelanceProject(models.Model):

    title = models.CharField(max_length=255)
    repository = models.URLField(max_length=255, help_text="Github repo where the event occured")
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    total_client_hourly_price = models.FloatField(
        help_text="How much will the client be billed for each our on this project"
    )

    def __str__(self):
        return self.title


class FreelanceProjectMember(models.Model):
    freelancer = models.ForeignKey(Freelancer, on_delete=models.CASCADE)
    project = models.ForeignKey(AcademyFreelanceProject, on_delete=models.CASCADE)
    total_cost_hourly_price = models.FloatField(
        null=True,
        blank=True,
        default=None,
        help_text="Paid to the freelancer, leave blank to use the default freelancer price",
    )
    total_client_hourly_price = models.FloatField(
        null=True,
        blank=True,
        default=None,
        help_text="Billed to the client on this project/freelancer, leave blank to use default from the project",
    )


DUE = "DUE"
APPROVED = "APPROVED"
PAID = "PAID"
IGNORED = "IGNORED"
BILL_STATUS = (
    (DUE, "Due"),
    (APPROVED, "Approved"),
    (IGNORED, "Ignored"),
    (PAID, "Paid"),
)


class ProjectInvoice(models.Model):
    status = models.CharField(max_length=20, choices=BILL_STATUS, default=DUE)

    total_duration_in_minutes = models.FloatField(default=0)
    total_duration_in_hours = models.FloatField(default=0)
    total_price = models.FloatField(default=0)

    project = models.ForeignKey(AcademyFreelanceProject, on_delete=models.CASCADE)

    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, null=True, default=None)
    paid_at = models.DateTimeField(null=True, default=None, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    @staticmethod
    def get_or_create(repository, academy_slug, status):

        invoice = ProjectInvoice.objects.filter(
            status=status, project__repository__iexact=repository, project__academy__slug=academy_slug
        ).first()
        if invoice is None:
            project = AcademyFreelanceProject.objects.filter(
                repository__iexact=repository, academy__slug=academy_slug
            ).first()
            if project is None:
                return None

            invoice = ProjectInvoice(project=project)
            invoice.save()

        return invoice


class Bill(models.Model):
    status = models.CharField(max_length=20, choices=BILL_STATUS, default=DUE)

    total_duration_in_minutes = models.FloatField(default=0)
    total_duration_in_hours = models.FloatField(default=0)
    total_price = models.FloatField(default=0)

    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        null=True,
        default=None,
        blank=True,
        help_text="Will help catalog billing grouped by academy",
    )

    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, null=True, default=None)
    freelancer = models.ForeignKey(Freelancer, on_delete=models.CASCADE)
    paid_at = models.DateTimeField(null=True, default=None, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


IGNORED = "IGNORED"
DRAFT = "DRAFT"
TODO = "TODO"
DOING = "DOING"
DONE = "DONE"
ISSUE_STATUS = (
    (IGNORED, "Ignored"),
    (DRAFT, "Draft"),
    (TODO, "Todo"),
    (DOING, "Doing"),
    (DONE, "Done"),
)


class Issue(models.Model):
    title = models.CharField(max_length=255)

    node_id = models.CharField(
        max_length=50,
        default=None,
        null=True,
        blank=True,
        help_text="This is the only unique identifier we get from github, the issue number is not unique among repos",
    )
    status = models.CharField(max_length=20, choices=ISSUE_STATUS, default=DRAFT)
    status_message = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        default=None,
        help_text="Important message like reason why not included on bill, etc.",
    )

    github_state = models.CharField(max_length=30, blank=True, null=True, default=None)
    github_number = models.PositiveIntegerField(blank=True, null=True, default=None)
    body = models.TextField(max_length=500)

    duration_in_minutes = models.FloatField(default=0)
    duration_in_hours = models.FloatField(default=0)

    url = models.URLField()
    repository_url = models.URLField(blank=True, default=None, null=True)

    author = models.ForeignKey(User, on_delete=models.CASCADE, null=True, default=None, blank=True)
    freelancer = models.ForeignKey(Freelancer, on_delete=models.CASCADE)

    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        null=True,
        default=None,
        blank=True,
        help_text="Will help catalog billing grouped by academy",
    )
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, null=True, default=None, blank=True)
    invoice = models.ForeignKey(
        ProjectInvoice,
        null=True,
        default=None,
        blank=True,
        on_delete=models.SET_DEFAULT,
        help_text="Attach this issue to a project invoice",
    )

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
