import logging, os
from django.dispatch import receiver
from django.db.models.signals import pre_delete
from .models import RepositorySubscription
from .tasks import async_unsubscribe_repo

logger = logging.getLogger(__name__)
