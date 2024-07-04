import logging
from django.core.management.base import BaseCommand
from ...models import Asset
from breathecode.authenticate.models import AcademyAuthSettings
from breathecode.monitoring.actions import subscribe_repository
from breathecode.monitoring.models import RepositorySubscription

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Set published date to legacy articles"

    def handle(self, *args, **options):

        assets = Asset.objects.filter(status="PUBLISHED", is_auto_subscribed=True, readme_url__isnull=False)
        settings = {}
        for a in assets:
            academy_id = str(a.academy.id)
            username, repo_name, branch_name = a.get_repo_meta()
            repo_url = f"https://github.com/{username}/{repo_name}"
            subs = RepositorySubscription.objects.filter(repository=repo_url).first()
            if subs is None:

                if academy_id not in settings:
                    settings[academy_id] = AcademyAuthSettings.objects.filter(academy__id=a.academy.id).first()
                    if settings[academy_id] is None:
                        logger.debug(f"Skipping asset {a.slug}, settings not found for academy {academy_id}")
                        continue

                subs = RepositorySubscription(
                    repository=repo_url,
                    owner=a.academy,
                )
                subs.save()

                try:
                    if settings[academy_id] is not None:
                        subs = subscribe_repository(subs.id, settings[academy_id])
                        logger.debug(
                            f"Successfully created asset subscription with status {subs.status} for {a.slug}, repo {repo_url}"
                        )
                    else:
                        raise Exception(f"No subscription found for academy {academy_id}")
                except Exception as e:
                    subs.status = "CRITICAL"
                    subs.status_message = str(e)
                    subs.save()
            else:
                logger.debug(f"Already subscribed to asset {a.slug} thru repo {repo_url}")

            if not a.is_auto_subscribed:
                logger.debug(f"Disabling asset {a.slug}, subscription because auto_subscribe is deactivated")
                subs.status = "DISABLED"
                continue
