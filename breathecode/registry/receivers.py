import logging, json
from django.dispatch import receiver
from django.db.models.signals import post_delete
from .models import Asset, AssetAlias, AssetImage
from .tasks import (async_regenerate_asset_readme, async_delete_asset_images, async_remove_img_from_cloud)
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


@receiver(asset_readme_modified, sender=Asset)
def post_asset_readme_modified(sender, instance: Asset, **kwargs):
    logger.debug('Cleaning asset raw readme')
    async_regenerate_asset_readme.delay(instance.slug)


@receiver(post_delete, sender=Asset)
def post_asset_deleted(sender, instance: Asset, **kwargs):
    logger.debug('Asset deleted, removing images from bucket and other cleanup steps')
    async_delete_asset_images.delay(instance.slug)


@receiver(post_delete, sender=AssetImage)
def post_assetimage_deleted(sender, instance: Asset, **kwargs):
    logger.debug('AssetImage deleted, removing image from buckets')
    async_remove_img_from_cloud.delay(instance.id)


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
