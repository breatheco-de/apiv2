import logging
from typing import Any, Type

from django.dispatch import receiver

from breathecode.media import settings
from breathecode.media.models import Chunk

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
            total_chunks=instance.total_chunks,
        )
        .exclude(id=instance.id)
        .exists()
    )
    if copy_exists is False:
        settings.del_temp_file(instance)

    instance.delete()
