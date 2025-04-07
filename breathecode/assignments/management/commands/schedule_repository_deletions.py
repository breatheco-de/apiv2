import re
from datetime import datetime
from typing import Any, Optional

from dateutil import parser
from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from breathecode.assignments import tasks
from breathecode.assignments.models import RepositoryDeletionOrder, RepositoryWhiteList, Task
from breathecode.authenticate.models import AcademyAuthSettings
from breathecode.monitoring.models import RepositorySubscription
from breathecode.registry.models import Asset
from breathecode.services.github import Github


class Command(BaseCommand):
    help = "Clean data from marketing module"
    github_url_pattern = re.compile(r"https?://github\.com/(?P<user>[^/\s]+)/(?P<repo>[^/\s]+)/?")
    allowed_users = ["breatheco-de", "4GeeksAcademy", "4geeksacademy"]

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
            self.delete_invalid_orders()

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
        """
        Get the username to transfer the repository to by fetching collaborators from the GitHub API.

        Instead of trying to determine the owner from the repository name, which is unreliable,
        we now get the list of collaborators from the repository and choose the most appropriate one.
        """
        # Get collaborators for the repository - treating it as an iterator
        eligible_collaborators = []

        for collaborators_page in self.github_client.get_repo_collaborators(owner, repo):
            # Filter out organization accounts and the allowed users (our own accounts)
            for collab in collaborators_page:
                if (
                    collab.get("login")
                    and collab.get("login") not in self.allowed_users
                    and collab.get("type") == "User"
                ):
                    eligible_collaborators.append(collab)

            # If we found at least one eligible collaborator, we can stop
            if eligible_collaborators:
                break

        if eligible_collaborators:
            # If we have eligible collaborators, return the first one
            return eligible_collaborators[0]["login"]

        # As a fallback, try to get the forker of the repository
        for events in self.github_client.get_repo_events(owner, repo):
            for event in events:
                if (
                    self.check_path(event, "type")
                    and event["type"] == "ForkEvent"
                    and self.check_path(event, "actor", "login")
                ):
                    return event["actor"]["login"]

        # If there was an error, fall back to the old method as a last resort
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
        ids = []

        page = 0
        to_delete = []
        while True:
            qs = RepositoryDeletionOrder.objects.exclude(
                status__in=[RepositoryDeletionOrder.Status.TRANSFERRED, RepositoryDeletionOrder.Status.DELETED],
                id__in=ids,
            )[page * 100 : (page + 1) * 100]

            if len(qs) == 0:
                break

            for deletion_order in qs:
                ids.append(deletion_order.id)
                if deletion_order.repository_user not in self.allowed_users:
                    to_delete.append(deletion_order.id)
                    continue

                if RepositoryWhiteList.objects.filter(
                    provider=deletion_order.provider,
                    repository_user__iexact=deletion_order.repository_user,
                    repository_name__iexact=deletion_order.repository_name,
                ).exists():
                    to_delete.append(deletion_order.id)

            page += 1

        RepositoryDeletionOrder.objects.filter(id__in=to_delete).delete()

    def delete_invalid_orders(self):
        RepositoryDeletionOrder.objects.exclude(
            repository_user__in=self.allowed_users,
        ).delete()

    def delete_github_repositories(self):
        ids = []

        while True:
            qs = RepositoryDeletionOrder.objects.filter(
                Q(
                    status__in=[RepositoryDeletionOrder.Status.TRANSFERRING, RepositoryDeletionOrder.Status.ERROR],
                    starts_transferring_at__lte=timezone.now() - relativedelta(months=2),
                )
                | Q(
                    status__in=[RepositoryDeletionOrder.Status.PENDING, RepositoryDeletionOrder.Status.ERROR],
                    created_at__lte=timezone.now() - relativedelta(months=2),
                ),
                repository_user__in=self.allowed_users,
                provider=RepositoryDeletionOrder.Provider.GITHUB,
            ).exclude(id__in=ids)[:100]

            if qs.count() == 0:
                break

            for deletion_order in qs:
                ids.append(deletion_order.id)

                if deletion_order.repository_name.endswith(".git"):
                    deletion_order.repository_name = deletion_order.repository_name[:-4]
                    deletion_order.save()

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
        if user not in self.allowed_users:
            return

        if RepositoryWhiteList.objects.filter(
            provider=provider, repository_user=user, repository_name=repo_name
        ).exists():
            return

        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]

        # Default status
        status = RepositoryDeletionOrder.Status.PENDING

        # Try to find tasks related to this repository
        related_tasks = Task.objects.filter(github_url__icontains=f"github.com/{user}/{repo_name}")

        # Check if we have tasks that aren't pending
        if related_tasks.exclude(revision_status=Task.RevisionStatus.PENDING).exists():
            status = RepositoryDeletionOrder.Status.NO_STARTED

        # Try to find a user to associate with the deletion order
        user_id = None
        if possible_user := related_tasks.exclude(user_id=None).only("user_id").first():
            user_id = possible_user.user_id

        # Create or get the deletion order
        order, _ = RepositoryDeletionOrder.objects.get_or_create(
            provider=provider,
            repository_user=user,
            repository_name=repo_name,
            defaults={"status": status, "user_id": user_id},
        )

        # Update status if needed
        if order.status != status:
            order.status = status
            order.save()

        # If the order doesn't have a user but we found one, update it
        if order.user_id is None and user_id is not None:
            order.user_id = user_id
            order.save()

    def collect_transferred_orders(self):
        ids = []

        while True:
            qs = RepositoryDeletionOrder.objects.filter(
                repository_user__in=self.allowed_users,
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
                repository_user__in=self.allowed_users,
                provider=RepositoryDeletionOrder.Provider.GITHUB,
                status__in=[RepositoryDeletionOrder.Status.PENDING, RepositoryDeletionOrder.Status.ERROR],
                created_at__gt=timezone.now(),
            ).exclude(id__in=ids)[:100]

            if qs.count() == 0:
                break

            for deletion_order in qs:
                ids.append(deletion_order.id)

                if deletion_order.repository_name.endswith(".git"):
                    deletion_order.repository_name = deletion_order.repository_name[:-4]
                    deletion_order.save()

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

                        tasks.send_repository_deletion_notification.delay(deletion_order.id, new_owner)

                except Exception as e:
                    deletion_order.status = RepositoryDeletionOrder.Status.ERROR
                    deletion_order.status_text = str(e)
                    deletion_order.save()
