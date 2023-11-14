import logging, os
from celery import shared_task
from django.contrib.auth.models import User
from breathecode.authenticate.models import UserInvite
from breathecode.marketing.actions import validate_email
from breathecode.utils.decorators import task, RetryTask

from breathecode.utils.decorators.task import AbortTask, TaskPriority, task
from breathecode.utils.validation_exception import ValidationException
from .actions import set_gitpod_user_expiration, add_to_organization, remove_from_organization
from breathecode.notify import actions as notify_actions

API_URL = os.getenv('API_URL', '')

logger = logging.getLogger(__name__)


@task(bind=True)
def async_validate_email_invite(self, invite_id, task_manager_id):
    logger.debug(f'Validating email for invite {invite_id}')
    user_invite = UserInvite.objects.filter(id=invite_id).first()

    if user_invite is None:
        raise AbortTask(f'UserInvite {invite_id} not found')

    try:
        email_status = validate_email(user_invite.email, 'en')
        if email_status['score'] <= 0.60:
            user_invite.process_status = 'ERROR'
            user_invite.process_message = 'Your email is invalid'
        user_invite.email_quality = email_status['score']
        user_invite.email_status = email_status

    except ValidationException as e:
        user_invite.process_status = 'ERROR'
        user_invite.process_message = str(e)

    except Exception:
        raise RetryTask(f'Retrying email validation for invite {invite_id}')

    user_invite.save()

    return True


@shared_task(priority=TaskPriority.ACADEMY.value)
def async_set_gitpod_user_expiration(gitpoduser_id):
    logger.debug(f'Recalculate gitpoduser expiration for {gitpoduser_id}')
    return set_gitpod_user_expiration(gitpoduser_id) is not None


@shared_task(priority=TaskPriority.ACADEMY.value)
def async_add_to_organization(cohort_id, user_id):
    return add_to_organization(cohort_id, user_id)


@shared_task(priority=TaskPriority.ACADEMY.value)
def async_remove_from_organization(cohort_id, user_id, force=False):
    return remove_from_organization(cohort_id, user_id, force=force)


@shared_task(priority=TaskPriority.NOTIFICATION.value)
def async_accept_user_from_waiting_list(user_invite_id: int) -> None:
    from .models import UserInvite

    logger.debug(f'Process to accept UserInvite {user_invite_id}')

    if not (invite := UserInvite.objects.filter(id=user_invite_id).first()):
        logger.error(f'UserInvite {user_invite_id} not found')
        return

    if not invite.email:
        invite.status = 'ACCEPTED'
        invite.process_status = 'ERROR'
        invite.process_message = "Can't determine the user email"
        invite.save()
        return

    if user := User.objects.filter(email=invite.email).first():
        invite.status = 'ACCEPTED'
        invite.process_status = 'DONE'
        invite.process_message = f'User already exists with the id {user.id}'
        invite.save()
        return

    user = User(username=invite.email,
                email=invite.email,
                first_name=invite.first_name or '',
                last_name=invite.last_name or '')

    user.save()

    invite.user = user
    invite.status = 'ACCEPTED'
    invite.process_status = 'DONE'
    invite.process_message = f'Registered as User with id {user.id}'
    invite.save()

    notify_actions.send_email_message(
        'pick_password', user.email, {
            'SUBJECT': 'Set your password at 4Geeks',
            'LINK': os.getenv('API_URL', '') + f'/v1/auth/password/{invite.token}'
        })


@task(priority=TaskPriority.OAUTH_CREDENTIALS.value)
def destroy_legacy_key(legacy_key_id):
    from .models import LegacyKey

    LegacyKey.objects.filter(id=legacy_key_id).delete()
