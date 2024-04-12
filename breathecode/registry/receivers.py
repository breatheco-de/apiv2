import logging, os
from django.dispatch import receiver
from django.db.models.signals import post_delete
from .models import Asset, AssetAlias, AssetImage
from .tasks import (async_regenerate_asset_readme, async_delete_asset_images, async_remove_img_from_cloud,
                    async_synchonize_repository_content, async_create_asset_thumbnail_legacy,
                    async_add_syllabus_translations, async_update_frontend_asset_cache, async_create_asset_thumbnail)
from .signals import (asset_slug_modified, asset_readme_modified, asset_title_modified)
from breathecode.assignments.signals import assignment_created
from breathecode.assignments.models import Task

from breathecode.monitoring.signals import github_webhook
from breathecode.monitoring.models import RepositoryWebhook

from breathecode.admissions.models import SyllabusVersion
from breathecode.admissions.signals import syllabus_version_json_updated

logger = logging.getLogger(__name__)


@receiver(asset_slug_modified, sender=Asset)
def post_asset_slug_modified(sender, instance: Asset, **kwargs):
    logger.debug(f'Procesing asset slug creation for {instance.slug}')
    if instance.lang == 'en':
        instance.lang = 'us'

    # create a new slug alias but keep the old one for redirection purposes
    AssetAlias.objects.create(slug=instance.slug, asset=instance)

    # add the asset as the first translation
    a = Asset.objects.get(id=instance.id)
    a.all_translations.add(instance)
    instance.save()
    async_update_frontend_asset_cache.delay(instance.slug)


@receiver(asset_title_modified, sender=Asset)
def asset_title_was_updated(sender, instance, **kwargs):

    # ignore unpublished assets
    if instance.status != 'PUBLISHED':
        return False

    async_update_frontend_asset_cache.delay(instance.slug)

    bucket_name = os.getenv('SCREENSHOTS_BUCKET', None)
    if bucket_name is None or bucket_name == '':
        return False

    if instance.title is None or instance.title == '':
        return False

    # taking thumbnail for the first time
    if instance.preview is None or instance.preview == '':
        logger.debug('Creating asset screenshot')
        async_create_asset_thumbnail.delay(instance.slug)
        return True


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
        logger.debug(f'Ignoring task {instance.associated_slug} because its not an internal registry asset')
        return None

    # adding subtasks to assignment based on the readme from the task
    instance.subtasks = asset.get_tasks()
    instance.save()


@receiver(github_webhook, sender=RepositoryWebhook)
def post_webhook_received(sender, instance, **kwargs):
    if instance.scope in ['push']:
        logger.debug('Received github webhook signal for push')
        async_synchonize_repository_content.delay(instance.id)


@receiver(syllabus_version_json_updated, sender=SyllabusVersion)
def syllabus_json_updated(sender, instance, **kwargs):
    logger.debug(f'Syllabus Version json for {instance.syllabus.slug} was updated')
    async_add_syllabus_translations.delay(instance.syllabus.slug, instance.version)
