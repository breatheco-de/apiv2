import re
from datetime import datetime
from typing import Any, Optional

from dateutil import parser
from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from breathecode.assignments.models import RepositoryDeletionOrder, RepositoryWhiteList, Task
from breathecode.authenticate.models import AcademyAuthSettings
from breathecode.monitoring.models import RepositorySubscription
from breathecode.registry.models import Asset
from breathecode.services.github import Github


class Command(BaseCommand):
    help = "Clean data from marketing module"
    github_url_pattern = re.compile(r"https?:\/\/github\.com\/(?P<user>[^\/]+)\/(?P<repo>[^\/\s]+)\/?")

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
            self.collect_transferred_orders()
            self.transfer_ownership()
            self.delete_github_repositories()

    def check_path(self, obj: dict, *indexes: str) -> bool:
        try:
            value = obj
            for index in indexes:
                value = value[index]
            return True
        except Exception:
            return False

    def how_many_added_members(self, events: list[dict[str, Any]]) -> int:
        return len(
            [
                event
                for event in events
                if self.check_path(event, "type")
                and self.check_path(event, "payload", "action")
                and event["type"] == "MemberEvent"
                and event["payload"]["action"] == "added"
            ]
        )

    def get_username(self, owner: str, repo: str) -> Optional[str]:
        r = repo
        repo = repo.lower()
        index = -1
        for events in self.github_client.get_repo_events(owner, r):
            index += 1
            for event in events:
                if self.check_path(event, "type") is False:
                    continue

                if (
                    index == 0
                    and event["type"] == "MemberEvent"
                    and len(events) < 30
                    and self.check_path(event, "payload", "action")
                    and self.how_many_added_members(events) == 1
                    and self.check_path(event, "payload", "member", "login")
                    and event["payload"]["action"] == "added"
                ):
                    return event["payload"]["member"]["login"]

                if (
                    event["type"] == "watchEvent"
                    and self.check_path(event, "actor", "login")
                    and event["actor"]["login"].replace("-", "").lower() in repo
                ):
                    return event["actor"]["login"]

                if (
                    event["type"] == "MemberEvent"
                    and self.check_path(event, "payload", "member", "login")
                    and event["payload"]["member"]["login"].replace("-", "").lower() in repo
                ):
                    return event["payload"]["member"]["login"]

                if (
                    event["type"] == "IssuesEvent"
                    and self.check_path(event, "payload", "assignee", "login")
                    and event["payload"]["assignee"]["login"].replace("-", "").lower() in repo
                ):
                    return event["payload"]["assignee"]["login"]

                if (
                    self.check_path(event, "actor", "login")
                    and event["actor"]["login"].replace("-", "").lower() in repo
                ):
                    return event["actor"]["login"]

    def purge_deletion_orders(self):

        page = 0
        to_delete = []
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
                    to_delete.append(deletion_order.id)

            page += 1

        RepositoryDeletionOrder.objects.filter(id__in=to_delete).delete()

    def delete_github_repositories(self):

        while True:
            qs = RepositoryDeletionOrder.objects.filter(
                Q(
                    status=RepositoryDeletionOrder.Status.TRANSFERRING,
                    starts_transferring_at__lte=timezone.now() - relativedelta(months=2),
                )
                | Q(
                    status=RepositoryDeletionOrder.Status.PENDING,
                    created_at__lte=timezone.now() - relativedelta(months=2),
                ),
                provider=RepositoryDeletionOrder.Provider.GITHUB,
            )[:100]

            if qs.count() == 0:
                break

            for deletion_order in qs:
                try:
                    if self.github_client.repo_exists(
                        owner=deletion_order.repository_user, repo=deletion_order.repository_name
                    ):
                        self.github_client.delete_org_repo(
                            owner=deletion_order.repository_user, repo=deletion_order.repository_name
                        )
                        deletion_order.status = RepositoryDeletionOrder.Status.DELETED
                        deletion_order.save()

                    elif deletion_order.status == RepositoryDeletionOrder.Status.TRANSFERRING:
                        deletion_order.status = RepositoryDeletionOrder.Status.TRANSFERRED
                        deletion_order.save()

                    else:
                        raise Exception(
                            f"Repository does not exist: {deletion_order.repository_user}/{deletion_order.repository_name}"
                        )

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
                asset.template_url,
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

        status = RepositoryDeletionOrder.Status.PENDING
        if (
            Task.objects.filter(github_url__icontains=f"github.com/{user}/{repo_name}")
            .exclude(revision_status=Task.RevisionStatus.PENDING)
            .exists()
        ):
            status = RepositoryDeletionOrder.Status.NO_STARTED

        order, _ = RepositoryDeletionOrder.objects.get_or_create(
            provider=provider,
            repository_user=user,
            repository_name=repo_name,
            defaults={"status": status},
        )

        if order.status != status:
            order.status = status
            order.save()

    def collect_transferred_orders(self):

        ids = []

        while True:
            qs = RepositoryDeletionOrder.objects.filter(
                provider=RepositoryDeletionOrder.Provider.GITHUB,
                status=RepositoryDeletionOrder.Status.TRANSFERRING,
                created_at__gt=timezone.now(),
            ).exclude(id__in=ids)[:100]

            if qs.count() == 0:
                break

            for deletion_order in qs:
                try:
                    ids.append(deletion_order.id)
                    if (
                        self.github_client.repo_exists(
                            owner=deletion_order.repository_user, repo=deletion_order.repository_name
                        )
                        is False
                    ):
                        deletion_order.status = RepositoryDeletionOrder.Status.TRANSFERRED
                        deletion_order.save()

                except Exception as e:
                    deletion_order.status = RepositoryDeletionOrder.Status.ERROR
                    deletion_order.status_text = str(e)
                    deletion_order.save()

    def transfer_ownership(self):
        ids = []

        while True:
            qs = RepositoryDeletionOrder.objects.filter(
                provider=RepositoryDeletionOrder.Provider.GITHUB,
                status=RepositoryDeletionOrder.Status.PENDING,
                created_at__gt=timezone.now(),
            ).exclude(id__in=ids)[:100]

            if qs.count() == 0:
                break

            for deletion_order in qs:
                ids.append(deletion_order.id)
                try:
                    if self.github_client.repo_exists(
                        owner=deletion_order.repository_user, repo=deletion_order.repository_name
                    ):
                        new_owner = self.get_username(deletion_order.repository_user, deletion_order.repository_name)
                        if not new_owner:
                            continue

                        self.github_client.transfer_repo(repo=deletion_order.repository_name, new_owner=new_owner)
                        deletion_order.status = RepositoryDeletionOrder.Status.TRANSFERRING
                        deletion_order.save()

                except Exception as e:
                    deletion_order.status = RepositoryDeletionOrder.Status.ERROR
                    deletion_order.status_text = str(e)
                    deletion_order.save()
