import os, re, json, logging
from itertools import chain
# from .models import Freelancer, Issue, Bill, RepositoryIssueWebhook
from rest_framework.exceptions import APIException, ValidationError, PermissionDenied

logger = logging.getLogger(__name__)


def close_mentoring_session(session, data):
    logger.debug(f'Ending mentoring {session.id} session with status {data["status"]}')
    session.summary = data['summary']
    session.status = data['status'].upper()
    session.save()
    return session
