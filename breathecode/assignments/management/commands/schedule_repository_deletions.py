import re
from datetime import datetime
from typing import Optional

from dateutil import parser
from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from breathecode.assignments.models import RepositoryDeletionOrder, RepositoryWhiteList
from breathecode.authenticate.models import AcademyAuthSettings
from breathecode.monitoring.models import RepositorySubscription
from breathecode.registry.models import Asset
from breathecode.services.github import Github


class Command(BaseCommand):
    help = "Clean data from marketing module"
    github_url_pattern = re.compile(r"https:\/\/github\.com\/(?P<user>[^\/]+)\/(?P<repo>[^\/\s]+)\/?")

    def handle(self, *args, **options):
        self.fill_whitelist()
        self.purge_deletion_orders()
        self.github()

    def github(self):
        processed = set()
        for settings in AcademyAuthSettings.objects.filter(
            github_owner__isnull=False, github_owner__credentialsgithub__isnull=False
        ).exclude(github_username=""):
            self.github_client = Github(
                org=settings.github_username, token=settings.github_owner.credentialsgithub.token
            )

            key = (settings.github_username, settings.github_owner.id)
            if key in processed:
                continue

            processed.add(key)
            last_check = None

            last = (
                RepositoryDeletionOrder.objects.filter(provider=RepositoryDeletionOrder.Provider.GITHUB)
                .only("created_at")
                .last()
            )
            if last:
                last_check = last.created_at

            self.schedule_github_deletions(settings.github_username, last_check)
            self.delete_github_repositories()

    def purge_deletion_orders(self):

        page = 0
        while True:
            qs = RepositoryDeletionOrder.objects.filter(
                status=RepositoryDeletionOrder.Status.PENDING,
            )[page * 100 : (page + 1) * 100]

            if len(qs) == 0:
                break

            for deletion_order in qs:
                if RepositoryWhiteList.objects.filter(
                    provider=deletion_order.provider,
                    repository_user__iexact=deletion_order.repository_user,
                    repository_name__iexact=deletion_order.repository_name,
                ).exists():
                    deletion_order.delete()

            page += 1

    def delete_github_repositories(self):

        while True:
            qs = RepositoryDeletionOrder.objects.filter(
                provider=RepositoryDeletionOrder.Provider.GITHUB,
                status=RepositoryDeletionOrder.Status.PENDING,
                created_at__lte=timezone.now() - relativedelta(months=2),
            )[:100]

            if qs.count() == 0:
                break

            for deletion_order in qs:
                try:
                    self.github_client.delete_org_repo(
                        owner=deletion_order.repository_user, repo=deletion_order.repository_name
                    )
                    deletion_order.status = RepositoryDeletionOrder.Status.DELETED
                    deletion_order.save()

                except Exception as e:
                    deletion_order.status = RepositoryDeletionOrder.Status.ERROR
                    deletion_order.status_text = str(e)
                    deletion_order.save()

    def fill_whitelist(self):
        assets = Asset.objects.filter()

        for asset in assets:
            options = [
                asset.url,
                asset.solution_url,
                asset.preview,
                asset.readme_url,
                asset.intro_video_url,
                asset.solution_video_url,
            ]
            for url in [x for x in options if x]:
                match = self.github_url_pattern.search(url)
                if match:
                    user = match.group("user")
                    repo_name = match.group("repo")

                    self.add_to_whitelist("GITHUB", user, repo_name)

            readme_raw = Asset.decode(asset.readme_raw)
            if readme_raw is None:
                continue

            urls = self.github_url_pattern.findall(readme_raw)

            for match in urls:
                user, repo_name = match

                self.add_to_whitelist("GITHUB", user, repo_name)

                assets = Asset.objects.filter()

        subscriptions = RepositorySubscription.objects.filter()
        for subscription in subscriptions:
            match = self.github_url_pattern.search(subscription.repository)
            if match:
                user = match.group("user")
                repo_name = match.group("repo")

                self.add_to_whitelist("GITHUB", user, repo_name)

    def add_to_whitelist(self, provider: str, user: str, repo_name: str):
        if (
            RepositoryWhiteList.objects.filter(
                provider=provider, repository_user__iexact=user, repository_name__iexact=repo_name
            ).exists()
            is False
        ):
            RepositoryWhiteList.objects.get_or_create(
                provider=provider, repository_user=user, repository_name=repo_name
            )

    def schedule_github_deletions(self, organization: str, last_check: Optional[datetime] = None):
        for repos in self.github_client.get_org_repos(
            organization, type="forks", per_page=30, direction="desc", sort="created"
        ):
            for repo in repos:
                created_at = parser.parse(repo["created_at"])

                if last_check and last_check > created_at:
                    return

                if repo["fork"] is True and repo["is_template"] is False and repo["allow_forking"] is True:
                    match = self.github_url_pattern.search(repo["html_url"])
                    if match:
                        user = match.group("user")
                        repo_name = match.group("repo")
                        self.schedule_github_deletion("GITHUB", user, repo_name)

    def schedule_github_deletion(self, provider: str, user: str, repo_name: str):
        if RepositoryWhiteList.objects.filter(
            provider=provider, repository_user=user, repository_name=repo_name
        ).exists():
            return

        RepositoryDeletionOrder.objects.get_or_create(
            provider=provider, repository_user=user, repository_name=repo_name
        )
