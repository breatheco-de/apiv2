import os
import logging
import random
from django.core.management.base import BaseCommand
from breathecode.authenticate.models import Profile

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sync academies from old breathecode"

    def handle(self, *args, **options):
        api_url = os.getenv("API_URL", "")
        current_avatar_url = api_url + "/static/img/avatar.png"

        pending = Profile.objects.filter(avatar_url=current_avatar_url)
        for profile in pending:
            avatar_number = random.randint(1, 21)
            avatar_url = api_url + f"/static/img/avatar-{avatar_number}.png"
            profile.avatar_url = avatar_url
            profile.save()

        logger.info(f"Fixing {pending.count()} avatars")
