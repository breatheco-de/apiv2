import os, re, json, logging
from itertools import chain
from .models import Freelancer, Issue, Bill, RepositoryIssueWebhook
from breathecode.authenticate.models import CredentialsGithub
from schema import Schema, And, Use, Optional, SchemaError
from rest_framework.exceptions import APIException, ValidationError, PermissionDenied
from github import Github

logger = logging.getLogger(__name__)


def get_hours(content):
    p = re.compile('<hrs>(\d+\.?\d*)</hrs>')
    result = p.search(content)
    hours = None
    if result is not None:
        hours = float(result.group(1))
    return hours


def get_status(content):
    p = re.compile('<status>(\d+\.?\d*)</status>')
    result = p.search(content)
    status = None
    if result is not None:
        status = result.group(1).upper()
    return status


def update_status_based_on_github_action(github_action, issue):
    # Possible github action:
    # opened, edited, deleted, pinned, unpinned, closed, reopened, assigned, unassigned, labeled, unlabeled, locked, unlocked, transferred, milestoned, or demilestoned.
    if issue is None:
        return 'DRAFT'

    if issue.status == 'IGNORED':
        return 'IGNORED'

    if github_action == 'reopened':
        return 'TODO'

    if github_action == 'deleted':
        return 'IGNORED'

    if github_action == 'closed':
        return 'DONE'

    return issue.status


def sync_single_issue(issue, comment=None, freelancer=None, incoming_github_action=None):

    if isinstance(issue, dict) == False:
        issue = {
            'id': issue.number,
            'title': issue.title,
            'body': issue.body,
            'html_url': issue.html_url,
            'assignees': [({
                'id': a.id
            }) for a in issue.assignees],
        }

    if 'issue' in issue:
        issue = issue['issue']

    issue_id = None
    if 'number' in issue:
        issue_id = issue['number']
    elif 'id' in issue:
        issue_id = issue['id']

    _issue = Issue.objects.filter(github_number=issue_id).first()

    if _issue is None:
        _issue = Issue(
            title='Untitled',
            github_number=issue_id,
        )

    if _issue.status in ['DONE', 'IGNORED'] and incoming_github_action not in ['reopened']:
        logger.debug(
            f'Ignoring changes to this issue {issue_id} because status is {_issue.status} and its not being reponened: {_issue.title}'
        )
        return _issue

    if issue['title'] is not None:
        _issue.title = issue['title'][:255]

    if issue['body'] is not None:
        _issue.body = issue['body'][:500]

    _issue.url = issue['html_url']

    if freelancer is None:
        if 'assignees' in issue and len(issue['assignees']) > 0:
            assigne = issue['assignees'][0]
            freelancer = Freelancer.objects.filter(github_user__github_id=assigne['id']).first()
            if freelancer is None:
                raise Exception(
                    f'Assined github user: {assigne["id"]} is not a freelancer but is the main user asociated to this issue'
                )

    _issue.freelancer = freelancer
    hours = get_hours(_issue.body)
    if hours is not None and _issue.duration_in_hours != hours:
        logger.debug(f'Updating issue {issue_id} hrs with {hours}, found <hrs> tag on updated body')
        _issue.duration_in_minutes = hours * 60
        _issue.duration_in_hours = hours

    # update based on the comment (if available)
    if comment is not None:
        hours = get_hours(comment['body'])
        if hours is not None and _issue.duration_in_hours != hours:
            logger.debug(f'Updating issue {issue_id} hrs with {hours}, found <hrs> tag on new comment')
            _issue.duration_in_minutes = hours * 60
            _issue.duration_in_hours = hours

        status = get_status(comment['body'])
        if status is not None:
            logger.debug(f'Updating issue {issue_id} status to {status} found <status> tag on new comment')
            _issue.status = status

    _issue.save()

    return _issue


def sync_user_issues(freelancer):

    if freelancer.github_user is None:
        raise ValueError(f'Freelancer has not github user')

    github_id = freelancer.github_user.github_id
    credentials = CredentialsGithub.objects.filter(github_id=github_id).first()
    if credentials is None:
        raise ValueError(f'Credentials for this user {gitub_user_id} not found')

    g = Github(credentials.token)
    user = g.get_user()
    open_issues = user.get_user_issues(state='open')
    for issue in open_issues:
        sync_single_issue(issue, freelancer=freelancer)

    return None


def change_status(issue, status):
    issue.status = status
    issue.save()
    return None


def generate_freelancer_bill(freelancer):

    Issue.objects.filter(status='TODO', bill__isnull=False).update(bill=None)

    open_bill = Bill.objects.filter(freelancer__id=freelancer.id, status='DUE').first()
    if open_bill is None:
        open_bill = Bill(freelancer=freelancer, )
        open_bill.save()

    done_issues = Issue.objects.filter(status='DONE', bill__isnull=True)
    total = {
        'minutes': open_bill.total_duration_in_minutes,
        'hours': open_bill.total_duration_in_hours,
        'price': open_bill.total_price
    }
    print(f'{done_issues.count()} issues found')
    for issue in done_issues:
        issue.bill = open_bill
        issue.save()
        total['hours'] = total['hours'] + issue.duration_in_hours
        total['minutes'] = total['minutes'] + issue.duration_in_minutes
    total['price'] = total['hours'] * freelancer.price_per_hour

    open_bill.total_duration_in_hours = total['hours']
    open_bill.total_duration_in_minutes = total['minutes']
    open_bill.total_price = total['price']
    open_bill.save()

    return open_bill


def run_hook(modeladmin, request, queryset):
    # TODO: ActiveCampaign and acp_ids is not defined
    for hook in queryset.all():
        ac_academy = hook.ac_academy
        client = ActiveCampaign(ac_academy.ac_key, ac_academy.ac_url)
        client.execute_action(hook.id, acp_ids)


run_hook.short_description = 'Process Hook'


def add_webhook(context: dict, academy_slug: str):
    """Add one incoming webhook request to log"""

    if not context or not len(context):
        return None

    webhook = RepositoryIssueWebhook(webhook_action=context['action'], academy_slug=academy_slug)

    if 'repository' in context:
        webhook.repository = context['repository']['html_url']

    webhook.payload = json.dumps(context)
    webhook.status = 'PENDING'
    webhook.save()

    return webhook
