import logging
from breathecode.admissions.signals import syllabus_asset_slug_updated
from .models import Task
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(syllabus_asset_slug_updated)
def process_syllabus_asset_slug_updated(sender, **kwargs):

    from_slug = kwargs.pop('from_slug', None)
    to_slug = kwargs.pop('to_slug', None)
    asset_type = kwargs.pop('asset_type', None)

    tasks = Task.objects.filter(associated_slug=from_slug,
                                task_type=asset_type.upper()).update(associated_slug=to_slug)
    logger.debug(
        f'{asset_type} slug {from_slug} was replaced with {to_slug} on all the syllabus, as a sideeffect we are replacing the slug also on the student tasks'
    )
