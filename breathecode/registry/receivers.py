import logging
import os

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from breathecode.admissions.models import SyllabusVersion
from breathecode.admissions.signals import syllabus_version_json_updated
from breathecode.assessment.models import Option, Question
from breathecode.assignments.models import Task
from breathecode.assignments.signals import assignment_created
from breathecode.monitoring.models import RepositoryWebhook
from breathecode.monitoring.signals import github_webhook

from .models import Asset, AssetAlias, AssetImage
from .signals import asset_readme_modified, asset_slug_modified, asset_title_modified
from .tasks import (
    async_add_syllabus_translations,
    async_create_asset_thumbnail,
    async_delete_asset_images,
    async_generate_quiz_config,
    async_regenerate_asset_readme,
    async_remove_img_from_cloud,
    async_synchonize_repository_content,
    async_update_frontend_asset_cache,
)

logger = logging.getLogger(__name__)


@receiver(asset_slug_modified, sender=Asset)
def post_asset_slug_modified(sender, instance: Asset, **kwargs):
    logger.debug(f"Procesing asset slug creation for {instance.slug}")
    if instance.lang == "en":
        instance.lang = "us"

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
    if instance.status != "PUBLISHED":
        return False

    async_update_frontend_asset_cache.delay(instance.slug)

    bucket_name = os.getenv("SCREENSHOTS_BUCKET", None)
    if bucket_name is None or bucket_name == "":
        return False

    if instance.title is None or instance.title == "":
        return False

    # taking thumbnail for the first time
    if instance.preview is None or instance.preview == "":
        logger.debug("Creating asset screenshot")
        async_create_asset_thumbnail.delay(instance.slug)
        return True

    # retaking a thumbnail if it was generated automatically
    # we know this because bucket_name is inside instance.preview
    if bucket_name in instance.preview:
        logger.debug("Retaking asset screenshot because title was updated")
        async_create_asset_thumbnail.delay(instance.slug)
        return True


@receiver(asset_readme_modified, sender=Asset)
def post_asset_readme_modified(sender, instance: Asset, **kwargs):
    logger.debug("Cleaning asset raw readme")
    async_regenerate_asset_readme.delay(instance.slug)


@receiver(post_delete, sender=Asset)
def post_asset_deleted(sender, instance: Asset, **kwargs):
    logger.debug("Asset deleted, removing images from bucket and other cleanup steps")
    async_delete_asset_images.delay(instance.slug)


@receiver(post_delete, sender=AssetImage)
def post_assetimage_deleted(sender, instance: Asset, **kwargs):
    logger.debug("AssetImage deleted, removing image from buckets")
    async_remove_img_from_cloud.delay(instance.id)


@receiver(assignment_created, sender=Task)
def post_assignment_created(sender, instance: Task, **kwargs):
    logger.debug("Adding substasks to created assignments")

    asset = Asset.objects.filter(slug=instance.associated_slug).first()
    if asset is None:
        logger.debug(f"Ignoring task {instance.associated_slug} because its not an internal registry asset")
        return None

    # adding subtasks to assignment based on the readme from the task
    instance.subtasks = asset.get_tasks()
    instance.save()


@receiver(github_webhook, sender=RepositoryWebhook)
def post_webhook_received(sender, instance, **kwargs):
    if instance.scope in ["push"]:
        logger.debug("Received github webhook signal for push")
        async_synchonize_repository_content.delay(instance.id)


@receiver(syllabus_version_json_updated, sender=SyllabusVersion)
def syllabus_json_updated(sender, instance, **kwargs):
    logger.debug(f"Syllabus Version json for {instance.syllabus.slug} was updated")
    async_add_syllabus_translations.delay(instance.syllabus.slug, instance.version)


## Keep assessment question and asset.config in synch


@receiver(post_save, sender=Question)
def model_a_saved(sender, instance, created, **kwargs):
    if not instance.assessment.is_archived:
        async_generate_quiz_config(instance.assessment.id)


@receiver(post_save, sender=Option)
def model_b_saved(sender, instance, created, **kwargs):
    if not instance.question.assessment.is_archived:
        async_generate_quiz_config(instance.question.assessment.id)


@receiver(post_delete, sender=Question)
def model_a_deleted(sender, instance, **kwargs):
    try:
        if instance.assessment and not instance.assessment.is_archived:
            async_generate_quiz_config(instance.assessment.id)
    except Exception:
        pass


@receiver(post_delete, sender=Option)
def model_b_deleted(sender, instance, **kwargs):
    try:
        if instance.assessment and not instance.assessment.is_archived:
            async_generate_quiz_config(instance.question.assessment.id)
    except Exception:
        pass
