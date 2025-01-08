import logging
from typing import Any, Type

# from capyc.core.i18n import translation
from django.dispatch import receiver

from breathecode.admissions.signals import syllabus_asset_slug_updated
from breathecode.assignments import tasks

from .models import Task
from .signals import assignment_status_updated

# from breathecode.authenticate.actions import get_user_settings
# from breathecode.authenticate.models import CredentialsGithub
# from breathecode.notify.actions import send_email_message

# from .signals import status_updated

logger = logging.getLogger(__name__)


@receiver(syllabus_asset_slug_updated)
def process_syllabus_asset_slug_updated(sender, **kwargs):

    from_slug = kwargs.pop("from_slug", None)
    to_slug = kwargs.pop("to_slug", None)
    asset_type = kwargs.pop("asset_type", None)

    Task.objects.filter(associated_slug=from_slug, task_type=asset_type.upper()).update(associated_slug=to_slug)
    logger.debug(
        f"{asset_type} slug {from_slug} was replaced with {to_slug} on all the syllabus, as a sideeffect "
        "we are replacing the slug also on the student tasks"
    )


@receiver(assignment_status_updated, sender=Task)
def process_cohort_history_log(sender: Type[Task], instance: Task, **kwargs: Any):
    logger.info("Procesing Cohort history log for cohort: " + str(instance.id))

    tasks.set_cohort_user_assignments.delay(instance.id)


# @receiver(status_updated, sender=RepositoryDeletionOrder)
# def repository_deletion_order_status_updated(
#     sender: Type[RepositoryDeletionOrder], instance: RepositoryDeletionOrder, **kwargs: Any
# ):
#     logger.info("Procesing RepositoryDeletionOrder status updated for repository: " + str(instance.id))
#     if (
#         instance.status == RepositoryDeletionOrder.Status.TRANSFERRING
#         and instance.provider == RepositoryDeletionOrder.Provider.GITHUB
#     ) is False:
#         return

#     credentials = CredentialsGithub.objects.filter(username=instance.repository_user).first()

#     settings = get_user_settings(credentials.user.id)
#     lang = settings.lang

#     send_email_message(
#         "message",
#         credentials.user.email,
#         {
#             "SUBJECT": translation(
#                 lang,
#                 en=f"We are transfering the repository {instance.repository_name} to you",
#                 es=f"Te estamos transfiriendo el repositorio {instance.repository_name}",
#             ),
#             "MESSAGE": translation(
#                 lang,
#                 en=f"We are transfering the repository {instance.repository_name} to you, you have two "
#                 "months to accept the transfer before we delete it",
#                 es=f"Te estamos transfiriendo el repositorio {instance.repository_name}, tienes dos meses "
#                 "para aceptar la transferencia antes de que la eliminemos",
#             ),
#             "BUTTON": translation(
#                 lang,
#                 en="Go to the repository",
#                 es="Ir al repositorio",
#             ),
#             "LINK": f"https://github.com/{instance.repository_user}/{instance.repository_name}",
#         },
#     )
