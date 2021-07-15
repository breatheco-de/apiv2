import os, re
from itertools import chain
from .models import Freelancer, Issue, Bill
from breathecode.authenticate.models import CredentialsGithub
from schema import Schema, And, Use, Optional, SchemaError
from rest_framework.exceptions import APIException, ValidationError, PermissionDenied
from github import Github


def sync_user_issues(freelancer):

    if freelancer.github_user is None:
        raise ValueError(f'Freelancer has not github user')

    github_id = freelancer.github_user.github_id
    credentials = CredentialsGithub.objects.filter(github_id=github_id).first()
    if credentials is None:
        raise ValueError(
            f'Credentials for this user {gitub_user_id} not found')

    g = Github(credentials.token)
    user = g.get_user()
    open_issues = user.get_user_issues(state='open')
    for issue in open_issues:
        _issue = Issue.objects.filter(github_number=issue.number).first()

        p = re.compile('<hrs>(\d+\.?\d*)</hrs>')
        result = p.search(issue.body)
        hours = 0
        if result is not None:
            hours = float(result.group(1))

        if _issue is not None:
            _issue.duration_in_minutes = hours * 60
            _issue.duration_in_hours = hours
            _issue.save()
        else:
            new_issue = Issue(
                title=issue.title[:255],
                github_number=issue.number,
                body=issue.body[0:500],
                url=issue.html_url,
                freelancer=freelancer,
                duration_in_minutes=hours * 60,
                duration_in_hours=hours,
            )
            new_issue.save()

    return None


def change_status(issue, status):
    issue.status = status
    issue.save()
    return None


def generate_freelancer_bill(freelancer):

    Issue.objects.filter(status='TODO', bill__isnull=False).update(bill=None)

    open_bill = Bill.objects.filter(freelancer__id=freelancer.id,
                                    status='DUE').first()
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
