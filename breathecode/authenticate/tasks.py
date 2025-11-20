import asyncio
import logging
import os
from typing import Any

from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import ValidationException
from celery import shared_task
from django.contrib.auth.models import User
from django.utils import timezone
from task_manager.core.exceptions import AbortTask, RetryTask
from task_manager.django.decorators import task

from breathecode.authenticate.models import Cohort, CredentialsDiscord, UserInvite
from breathecode.marketing.actions import validate_email_local
from breathecode.notify import actions as notify_actions
from breathecode.payments.models import PlanFinancing, Subscription
from breathecode.services.discord import Discord
from breathecode.utils.decorators import TaskPriority

from .actions import (
    add_to_organization,
    get_user_settings,
    remove_from_organization,
    revoke_user_discord_permissions,
    set_gitpod_user_expiration,
)

API_URL = os.getenv("API_URL", "")

logger = logging.getLogger(__name__)


@task(priority=TaskPriority.REALTIME.value)
def async_validate_email_invite(invite_id, **_):
    logger.debug(f"Validating email for invite {invite_id}")

    user_invite = UserInvite.objects.filter(id=invite_id).first()

    if user_invite is None:
        raise RetryTask(f"UserInvite {invite_id} not found")

    try:
        email_status = validate_email_local(user_invite.email, "en")
        if email_status["score"] <= 0.60:
            user_invite.status = "REJECTED"
            user_invite.process_status = "ERROR"
            user_invite.process_message = "Your email is invalid"
        user_invite.email_quality = email_status["score"]
        user_invite.email_status = email_status

    except ValidationException as e:
        user_invite.status = "REJECTED"
        user_invite.process_status = "ERROR"
        user_invite.process_message = str(e)

    except Exception:
        raise RetryTask(f"Retrying email validation for invite {invite_id}")

    user_invite.save()

    return True


@shared_task(priority=TaskPriority.ACADEMY.value)
def async_set_gitpod_user_expiration(gitpoduser_id):
    logger.debug(f"Recalculate gitpoduser expiration for {gitpoduser_id}")
    return set_gitpod_user_expiration(gitpoduser_id) is not None


@shared_task(priority=TaskPriority.ACADEMY.value)
def async_add_to_organization(cohort_id, user_id):
    return add_to_organization(cohort_id, user_id)


@shared_task(priority=TaskPriority.ACADEMY.value)
def async_remove_from_organization(cohort_id, user_id, force=False):
    return remove_from_organization(cohort_id, user_id, force=force)


@shared_task(priority=TaskPriority.TWO_FACTOR_AUTH.value)
def join_user_to_discord_guild(
    user_id,
    access_token: str,
    discord_user_id: int,
    cohort_slug: str,
):
    logger.info("=== JOIN DISCORD TASK STARTED ===")
    cohort_academy = Cohort.objects.filter(slug=cohort_slug).prefetch_related("academy").first()
    if not cohort_academy:
        logger.warning(f"Cohort with slug '{cohort_slug}' not found")
        return
    cohorts = Cohort.objects.filter(cohortuser__user_id=user_id, academy=cohort_academy.academy.id).all()
    server_id = None
    role_ids = set()
    for cohort in cohorts:
        if cohort.shortcuts:
            for shortcut in cohort.shortcuts:
                if shortcut.get("label", None) == "Discord" and shortcut.get("server_id", None) is not None:
                    if server_id is None:
                        server_id = shortcut.get("server_id")
                    if shortcut.get("server_id") == server_id:
                        role_id = shortcut.get("role_id")
                        if role_id:
                            role_ids.add(role_id)

    if server_id is None:
        return

    discord_services = Discord(academy_id=cohort_academy.academy.id)
    try:
        join_status = discord_services.join_user_to_guild(
            access_token=access_token, guild_id=server_id, discord_user_id=discord_user_id
        )

        if join_status.status_code == 201:
            logger.info("User joined Discord guild successfully, saving credentials...")
            from breathecode.authenticate.actions import save_discord_credentials

            save_result = save_discord_credentials(
                user_id=user_id,
                discord_user_id=discord_user_id,
                guild_id=server_id,
                cohort_slug=cohort_slug,
            )
            if save_result:
                logger.info("Credentials saved, assigning roles...")
                for role_id in role_ids:
                    logger.debug(f"Assigning role {role_id} to user {user_id} in server {server_id}")
                    assign_discord_role_task.delay(
                        guild_id=server_id,
                        discord_user_id=discord_user_id,
                        role_id=role_id,
                        academy_id=cohort_academy.academy.id,
                    )
        elif join_status.status_code == 204:
            logger.debug(f"User already in server, assigning roles for user {user_id} in server {server_id}")
            for role_id in role_ids:
                assign_discord_role_task.delay(
                    guild_id=server_id,
                    discord_user_id=discord_user_id,
                    role_id=role_id,
                    academy_id=cohort_academy.academy.id,
                )
        else:
            logger.error(f"Unexpected join status: {join_status}")
            raise Exception(f"Failed to join Discord guild: {join_status}")

    except Exception as e:
        logger.error({str(e)})
        raise e


@shared_task(priority=TaskPriority.TWO_FACTOR_AUTH.value)
def assign_discord_role_task(guild_id: int, discord_user_id: int, role_id: int, academy_id: int):
    discord_service = Discord(academy_id=academy_id)
    try:
        result = discord_service.assign_role_to_user(guild_id, discord_user_id, role_id)

        if result == 204:
            return result
        else:
            logger.error(f"Role assignment failed: {result}")
            return result
    except Exception as e:
        raise Exception(f"Error assigning role to user: {str(e)}")


@shared_task(priority=TaskPriority.TWO_FACTOR_AUTH.value)
def remove_discord_role_task(guild_id: int, discord_user_id: int, role_id: int, academy_id: int):
    logger.info(f"Removing role {role_id} from user {discord_user_id} in guild {guild_id} for academy {academy_id}")
    discord_service = Discord(academy_id=academy_id)
    try:
        result = discord_service.remove_role_to_user(guild_id, discord_user_id, role_id)

        if result == 204:
            return result
        else:
            raise AbortTask(f"Error removing role to user: {result}")

    except Exception as e:
        raise AbortTask(str(e))


@shared_task(priority=TaskPriority.TWO_FACTOR_AUTH.value)
def delayed_revoke_discord_permissions(entity_id: int, entity_type: str, date_field: str, **_: Any):
    """
    Revoke ONLY Discord permissions when subscription/plan financing dates expire.
    """
    logger.info(f"Starting delayed_revoke_discord_permissions for {entity_type} {entity_id} ({date_field})")

    if entity_type == "subscription":
        instance = Subscription.objects.filter(id=entity_id).first()
    else:
        instance = PlanFinancing.objects.filter(id=entity_id).first()

    if not instance:
        raise AbortTask(f"{entity_type} with id {entity_id} not found")

    # Verify the date has actually expired
    utc_now = timezone.now()
    target_date = getattr(instance, date_field, None)

    if target_date and target_date > utc_now:
        raise AbortTask(f"{entity_type} {entity_id} {date_field} has not expired yet ({target_date})")

    if instance.status not in ["CANCELLED", "DEPRECATED", "PAYMENT_ISSUE", "EXPIRED", "ERROR"]:
        logger.info(f"{entity_type} {entity_id} is now {instance.status}, skipping Discord revoke")
        return

    from breathecode.payments.actions import user_has_active_4geeks_plus_plans

    if user_has_active_4geeks_plus_plans(instance.user):
        logger.info(f"User {instance.user.id} now has active paid plans, skipping Discord revoke")
        return

    discord_creds = CredentialsDiscord.objects.filter(user=instance.user).first()

    if not discord_creds:
        raise AbortTask(f"User {instance.user.id} has no Discord credentials, skipping revoke")

    revoke_user_discord_permissions(instance.user, instance.academy)

    logger.info(f"Discord permissions revoked for {entity_type} {entity_id}")


@shared_task(priority=TaskPriority.TWO_FACTOR_AUTH.value)
def send_discord_dm_task(discord_user_id: int, message: str, academy_id: int):
    discord_service = Discord(academy_id=academy_id)
    try:
        result = asyncio.run(discord_service.send_dm_to_user(discord_user_id, message))

        if result == 200:
            logger.info("DM sent successfully")
            return result
        if result == 204:
            logger.info("Channel not found")
            return result
    except Exception as e:
        raise AbortTask(f"Error sending DM: {str(e)}")


@shared_task(priority=TaskPriority.NOTIFICATION.value)
def async_accept_user_from_waiting_list(user_invite_id: int) -> None:
    from .models import UserInvite

    logger.debug(f"Process to accept UserInvite {user_invite_id}")

    if not (invite := UserInvite.objects.filter(id=user_invite_id).first()):
        logger.error(f"UserInvite {user_invite_id} not found")
        return

    if not invite.email:
        invite.status = "ACCEPTED"
        invite.process_status = "ERROR"
        invite.process_message = "Can't determine the user email"
        invite.save()
        return

    if user := User.objects.filter(email=invite.email).first():
        invite.status = "ACCEPTED"
        invite.process_status = "DONE"
        invite.process_message = f"User already exists with the id {user.id}"
        invite.save()
        return

    user = User(
        username=invite.email, email=invite.email, first_name=invite.first_name or "", last_name=invite.last_name or ""
    )

    user.save()

    invite.user = user
    invite.status = "ACCEPTED"
    invite.process_status = "DONE"
    invite.process_message = f"Registered as User with id {user.id}"
    invite.save()

    notify_actions.send_email_message(
        "pick_password",
        user.email,
        {
            "SUBJECT": "Set your password at 4Geeks",
            "LINK": os.getenv("API_URL", "") + f"/v1/auth/password/{invite.token}",
        },
        academy=invite.academy,
    )


@task(priority=TaskPriority.STUDENT.value)
def create_user_from_invite(user_invite_id: int, **_):
    logger.info("Running create_user_from_invite task")

    if not (
        user_invite := UserInvite.objects.filter(id=user_invite_id)
        .only("email", "first_name", "last_name", "status", "user_id", "token", "academy__id")
        .first()
    ):
        raise RetryTask("User invite not found")

    if user_invite.status != "ACCEPTED":
        raise AbortTask("User invite is not accepted")

    if user_invite.user or (user := User.objects.filter(email=user_invite.email).only("id").first()):
        if not user_invite.user:
            user_invite.user = user
            user_invite.save()

        raise AbortTask("User invite is already associated to a user")

    if not user_invite.email:
        raise AbortTask("No email found")

    user = User()
    user.username = user_invite.email
    user.email = user_invite.email
    user.first_name = user_invite.first_name or ""
    user.last_name = user_invite.last_name or ""
    user.save()

    if user_invite.token:
        academy_name = None
        if getattr(user_invite, "academy", None) and getattr(user_invite.academy, "white_labeled", False):
            academy_name = getattr(user_invite.academy, "name", None)
        subject = f"Set your password at {academy_name}" if academy_name else "Set your password at 4Geeks"

        notify_actions.send_email_message(
            "pick_password",
            user.email,
            {
                "SUBJECT": subject,
                "LINK": os.getenv("API_URL", "") + f"/v1/auth/password/{user_invite.token}",
            },
            academy=user_invite.academy,
        )


@task(priority=TaskPriority.STUDENT.value)
def verify_user_invite_email(user_invite_id: int, **_):
    logger.info("Running create_user_from_invite task")

    if not (user_invite := UserInvite.objects.filter(id=user_invite_id).first()):
        raise AbortTask(f"User invite {user_invite_id} not found")

    if user_invite.user is None:
        raise AbortTask(f"User not found for user invite {user_invite_id}")

    user = user_invite.user

    if UserInvite.objects.filter(user=user_invite.user, is_email_validated=True).exists():
        raise AbortTask(f"Email already validated for user {user.id}")

    settings = get_user_settings(user.id)
    subject = translation(
        settings.lang,
        en="4Geeks - Validate account",
        es="4Geeks - Valida tu cuenta",
    )

    notify_actions.send_email_message(
        "verify_email",
        user.email,
        {
            "SUBJECT": subject,
            "LANG": settings.lang,
            "LINK": os.getenv("API_URL", "") + f"/v1/auth/password/{user_invite.token}",
        },
        academy=user_invite.academy,
    )
