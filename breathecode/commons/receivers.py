import logging
from typing import Any, Type

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.db import models

import breathecode.commons.actions as actions

logger = logging.getLogger(__name__)


@receiver(post_save)
def clean_cache_after_save(sender: Type[models.Model], **_: Any):
    actions.clean_cache(sender)


@receiver(post_delete)
def clean_cache_after_delete(sender: Type[models.Model], **_: Any):
    actions.clean_cache(sender)
