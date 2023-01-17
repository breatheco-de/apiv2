import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

import breathecode.commons.actions as actions

logger = logging.getLogger(__name__)


@receiver(post_save)
def clean_cache_after_save(sender, **kwargs):
    key = hash(sender)
    actions.clean_cache(key)


@receiver(post_delete)
def clean_cache_after_delete(sender, **kwargs):
    key = hash(sender)
    actions.clean_cache(key)
