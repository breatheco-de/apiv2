import logging
from typing import Any, Type

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.db import models
from .signals import update_cache

import breathecode.commons.actions as actions

logger = logging.getLogger(__name__)


@receiver(post_save)
def on_save(*args: Any, **kwargs: Any):
    del kwargs['signal']
    update_cache.send(*args, **kwargs)


@receiver(post_delete)
def on_delete(*args: Any, **kwargs: Any):
    del kwargs['signal']
    update_cache.send(*args, **kwargs)


@receiver(update_cache)
def clean_cache(sender: Type[models.Model], **_: Any):
    actions.clean_cache(sender)
