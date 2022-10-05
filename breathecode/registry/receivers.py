import logging, json
from django.dispatch import receiver
from .models import Asset, AssetAlias
from .signals import asset_slug_modified, asset_readme_modified
from breathecode.assignments.signals import assignment_created
from breathecode.assignments.models import Task

logger = logging.getLogger(__name__)


@receiver(asset_slug_modified, sender=Asset)
def post_asset_slug_modified(sender, instance: Asset, **kwargs):
    logger.debug('Procesing asset slug creation')
    if instance.lang == 'en':
        instance.lang = 'us'

    # create a new slug alias but keep the old one for redirection purposes
    alias = AssetAlias.objects.create(slug=instance.slug, asset=instance)

    # add the asset as the first translation
    a = Asset.objects.get(id=instance.id)
    a.all_translations.add(instance)
    instance.save()


@receiver(assignment_created, sender=Task)
def post_assignment_created(sender, instance: Task, **kwargs):
    logger.debug('Adding substasks to created assignments')

    asset = Asset.objects.filter(slug=instance.associated_slug).first()
    if asset is None:
        logger.debug('Ignoring task {instance.associated_slug} because its not an internal registry asset')
        return None

    # adding subtasks to assignment based on the readme from the task
    instance.subtasks = asset.get_tasks()
    instance.save()
