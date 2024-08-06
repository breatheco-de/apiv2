import logging
from typing import Any, Type

from django.dispatch import receiver

from breathecode.media.models import Chunk, File

from ..services.google_cloud import Storage
from .signals import schedule_deletion

logger = logging.getLogger(__name__)


@receiver(schedule_deletion, sender=Chunk)
def schedule_chunk_deletion(sender: Type[Chunk], instance: Chunk, **kwargs: Any):

    copy_exists = (
        Chunk.objects.filter(
            user=instance.user,
            academy=instance.academy,
            name=instance.name,
            mime=instance.mime,
            chunk_size=instance.chunk_size,
            total_chunks=instance.total_chunks,
            max_chucks=instance.max_chucks,
        )
        .exclude(id=instance.id)
        .exists()
    )
    if copy_exists is False:

        storage = Storage()
        cloud_file = storage.file(instance.bucket, instance.file_name)
        cloud_file.delete()

    instance.delete()


@receiver(schedule_deletion, sender=File)
def schedule_file_deletion(sender: Type[File], instance: File, **kwargs: Any):

    copy_exists = (
        Chunk.objects.filter(
            hash=instance.hash,
        )
        .exclude(id=instance.id)
        .exists()
    )
    if copy_exists is False:
        storage = Storage()
        cloud_file = storage.file(instance.bucket, instance.file_name)
        cloud_file.delete()

    instance.delete()
