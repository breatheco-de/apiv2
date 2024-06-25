import functools
import logging
import os
from typing import Any, Type

from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

import breathecode.commons.actions as actions

from .signals import update_cache

logger = logging.getLogger(__name__)

ENABLE_LIST_OPTIONS = ['true', '1', 'yes', 'y']


@functools.lru_cache(maxsize=1)
def is_cache_enabled():
    return os.getenv('CACHE', '1').lower() in ENABLE_LIST_OPTIONS


@receiver(post_save)
def on_save(*args: Any, **kwargs: Any):
    del kwargs['signal']
    update_cache.send_robust(*args, **kwargs)


@receiver(post_delete)
def on_delete(*args: Any, **kwargs: Any):
    del kwargs['signal']
    update_cache.send_robust(*args, **kwargs)


@receiver(update_cache)
def clean_cache(sender: Type[models.Model], **_: Any):
    if not is_cache_enabled():
        logger.debug('Cache has been disabled')
        return

    actions.clean_cache(sender)
