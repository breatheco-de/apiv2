import logging
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
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
