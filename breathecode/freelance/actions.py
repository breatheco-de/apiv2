import logging
import re

from django.contrib import admin
from django.db.models import Q
from github import Github

from breathecode.admissions.models import Academy
from breathecode.authenticate.models import CredentialsGithub
from breathecode.services.activecampaign import ActiveCampaign

from .models import ISSUE_STATUS, Bill, Freelancer, Issue, ProjectInvoice

logger = logging.getLogger(__name__)


def get_hours(content):
    p = re.compile(r"<hrs>(\d+\.?\d*)</hrs>")
    result = p.search(content)
    hours = None
    if result is not None:
        hours = float(result.group(1))
    return hours


def get_status(content):
    p = re.compile("<status>(\\w+)</status>")
    result = p.search(content)
    status = None
    if result is not None:
        status = result.group(1).upper()
    return status


def status_is_valid(status):
    statuses = [x[0] for x in ISSUE_STATUS]
    return status in statuses


def update_status_based_on_github_action(github_action, issue):
    # Possible github action:
    # opened, edited, deleted, pinned, unpinned, closed, reopened, assigned, unassigned, labeled, unlabeled, locked, unlocked, transferred, milestoned, or demilestoned.
    if issue is None:
        return "DRAFT"

    if issue.status == "IGNORED":
        return "IGNORED"

    if github_action == "reopened":
        return "TODO"

    if github_action == "deleted":
        return "IGNORED"

    if github_action == "closed":
        return "DONE"

    return issue.status


def sync_single_issue(issue, comment=None, freelancer=None, incoming_github_action=None, academy_slug=None):

    if isinstance(issue, dict) == False:
        issue = {
            "id": issue.number,
            "title": issue.title,
            "url": issue.html_url,
            "body": issue.body,
            "html_url": issue.html_url,
            "assignees": [({"id": a.id}) for a in issue.assignees],
        }

    if "issue" in issue:
        issue = issue["issue"]

    issue_number = None
    if "number" in issue:
        issue_number = issue["number"]

    node_id = None
    if "node_id" in issue:
        node_id = issue["node_id"]
    else:
        logger.info(
            f"Impossible to identify issue because it does not have a node_id (number:{issue_number}), ignoring synch: "
            + str(issue)
        )
        return None

    _issue = Issue.objects.filter(node_id=node_id).first()

    if _issue is None:
        _issue = Issue(
            title="Untitled",
            node_id=node_id,
        )

    _issue.academy = Academy.objects.filter(slug=academy_slug).first()

    if issue_number is not None:
        _issue.github_number = issue_number

    if issue["title"] is not None:
        _issue.title = issue["title"][:255]

    if issue["body"] is not None:
        _issue.body = issue["body"][:500]

    _issue.url = issue["html_url"]

    result = re.search(r"github\.com\/([\w\-_]+)\/([\w\-_]+)\/.+", _issue.url)
    if result is not None:
        _issue.repository_url = f"https://github.com/{result.group(1)}/{result.group(2)}"

        # To include it on the next invoice
        _issue.invoice = ProjectInvoice.get_or_create(_issue.repository_url, academy_slug, status="DUE")

    if freelancer is None:
        if "assignees" in issue and len(issue["assignees"]) > 0:
            assigne = issue["assignees"][0]
            freelancer = Freelancer.objects.filter(github_user__github_id=assigne["id"]).first()
            if freelancer is None:
                raise Exception(
                    f'Assigned github user: {assigne["id"]} is not a freelancer but is the main user associated to this issue'
                )
        else:
            raise Exception("There was no freelancer associated with this issue")

    _issue.freelancer = freelancer
    hours = get_hours(_issue.body)
    if hours is not None and _issue.duration_in_hours != hours:
        logger.info(f"Updating issue {node_id} ({issue_number}) hrs with {hours}, found <hrs> tag on updated body")
        _issue.duration_in_minutes = hours * 60
        _issue.duration_in_hours = hours

    # update based on the comment (if available)
    if comment is not None:
        hours = get_hours(comment["body"])
        if hours is not None and _issue.duration_in_hours != hours:
            logger.info(f"Updating issue {node_id} ({issue_number}) hrs with {hours}, found <hrs> tag on new comment")
            _issue.duration_in_minutes = hours * 60
            _issue.duration_in_hours = hours

        status = get_status(comment["body"])
        if status is not None and status_is_valid(status):
            logger.info(
                f"Updating issue {node_id} ({issue_number}) status to {status} found <status> tag on new comment"
            )
            _issue.status = status

        elif status is not None:
            error = f"The status {status} is not valid"
            logger.info(error)
            _issue.status_message = error
    _issue.save()

    return _issue


def sync_user_issues(freelancer, academy_slug=None):

    if freelancer.github_user is None:
        raise ValueError("Freelancer has not github user")

    github_id = freelancer.github_user.github_id
    credentials = CredentialsGithub.objects.filter(github_id=github_id).first()
    if credentials is None:
        raise ValueError(f"Credentials for this user {github_id} not found")

    g = Github(credentials.token)
    user = g.get_user()

    open_issues = user.get_user_issues(state="open")

    count = 0
    for issue in open_issues:
        count += 1
        _i = sync_single_issue(issue, freelancer=freelancer, academy_slug=academy_slug)
        if _i is not None:
            logger.debug(f"{_i.node_id} synched")
    logger.debug(f"{str(count)} issues found for this Github user credentials {str(credentials)}")

    return count


def change_status(issue, status):
    issue.status = status
    issue.save()
    return None


def generate_project_invoice(project):
    logger.debug("Generate invoice for project %s", project.title)
    # reset all pending issues invoices, we'll start again
    Issue.objects.filter(invoice__project__id=project.id).exclude(status="DONE").update(invoice=None)

    # get next pending invoice
    invoice = ProjectInvoice.get_or_create(project.repository, project.academy.slug, status="DUE")

    # fetch for issues to be invoiced
    done_issues = Issue.objects.filter(
        academy__slug=project.academy.slug, url__icontains=project.repository, status="DONE"
    ).filter(Q(invoice__isnull=True) | Q(invoice__status="DUE"))

    invoices = {}

    for issue in done_issues:

        issue.invoice = invoice
        issue.status_message = ""

        if str(issue.invoice.id) not in invoices:
            invoices[str(issue.invoice.id)] = {"minutes": 0, "hours": 0, "price": 0, "instance": issue.invoice}

        if issue.status != "DONE":
            issue.status_message += "Issue is still " + issue.status
        if issue.node_id is None or issue.node_id == "":
            issue.status_message += "Github node id not found"

        if issue.status_message == "":
            _hours = invoices[str(issue.invoice.id)]["hours"] + issue.duration_in_hours
            invoices[str(issue.invoice.id)]["hours"] = _hours
            invoices[str(issue.invoice.id)]["minutes"] = (
                invoices[str(issue.invoice.id)]["minutes"] + issue.duration_in_minutes
            )
            invoices[str(issue.invoice.id)]["price"] = _hours * issue.freelancer.get_client_hourly_rate(project)
        issue.save()

    for inv_id in invoices:
        invoices[inv_id]["instance"].total_duration_in_hours = invoices[inv_id]["hours"]
        invoices[inv_id]["instance"].total_duration_in_minutes = invoices[inv_id]["minutes"]
        invoices[inv_id]["instance"].total_price = invoices[inv_id]["price"]

        invoices[inv_id]["instance"].save()

    return [invoices[inv_id]["instance"] for inv_id in invoices]


def generate_freelancer_bill(freelancer):

    Issue.objects.filter(bill__isnull=False, freelancer__id=freelancer.id).exclude(status="DONE").update(bill=None)

    def get_bill(academy):
        open_bill = Bill.objects.filter(
            freelancer__id=freelancer.id, status="DUE", academy__slug=academy.slug, academy__isnull=False
        ).first()
        if open_bill is None:
            open_bill = Bill(freelancer=freelancer, academy=academy)
            open_bill.save()
        return open_bill

    done_issues = (
        Issue.objects.filter(freelancer__id=freelancer.id, status="DONE")
        .filter(Q(bill__isnull=True) | Q(bill__status="DUE"))
        .exclude(academy__isnull=True)
    )
    bills = {}

    for issue in done_issues:

        issue.bill = get_bill(issue.academy)
        issue.status_message = ""

        if str(issue.bill.id) not in bills:
            bills[str(issue.bill.id)] = {"minutes": 0, "hours": 0, "price": 0, "instance": issue.bill}

        if issue.status != "DONE":
            issue.status_message += "Issue is still " + issue.status
        if issue.node_id is None or issue.node_id == "":
            issue.status_message += "Github node id not found"

        if issue.status_message == "":
            _hours = bills[str(issue.bill.id)]["hours"] + issue.duration_in_hours
            bills[str(issue.bill.id)]["hours"] = _hours
            bills[str(issue.bill.id)]["minutes"] = bills[str(issue.bill.id)]["minutes"] + issue.duration_in_minutes

            project = issue.invoice.project if issue.invoice is not None else None
            bills[str(issue.bill.id)]["price"] = _hours * freelancer.get_hourly_rate(project)

        issue.save()

    for bill_id in bills:
        bills[bill_id]["instance"].total_duration_in_hours = bills[bill_id]["hours"]
        bills[bill_id]["instance"].total_duration_in_minutes = bills[bill_id]["minutes"]
        bills[bill_id]["instance"].total_price = bills[bill_id]["price"]
        bills[bill_id]["instance"].save()

    return [bills[bill_id]["instance"] for bill_id in bills]


@admin.display(description="Process Hook")
def run_hook(modeladmin, request, queryset):
    for hook in queryset.all():
        ac_academy = hook.ac_academy
        client = ActiveCampaign(ac_academy.ac_key, ac_academy.ac_url)
        client.execute_action(hook.id)
