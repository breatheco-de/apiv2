import re
from typing import Any, Optional

from django.core.management.base import BaseCommand

from breathecode.assignments import tasks
from breathecode.assignments.models import RepositoryDeletionOrder
from breathecode.authenticate.models import AcademyAuthSettings
from breathecode.services.github import Github


class Command(BaseCommand):
    help = "Clean data from marketing module"
    github_url_pattern = re.compile(r"https?://github\.com/(?P<user>[^/\s]+)/(?P<repo>[^/\s]+)/?")

    def handle(self, *args, **options):
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
            allowed_users = ["breatheco-de", "4GeeksAcademy", "4geeksacademy"]

            items = RepositoryDeletionOrder.objects.filter(provider=RepositoryDeletionOrder.Provider.GITHUB)
            for deletion_order in items:
                if deletion_order.repository_user not in allowed_users:
                    continue

                if deletion_order.repository_name.endswith(".git"):
                    deletion_order.repository_name = deletion_order.repository_name[:-4]
                    deletion_order.save()

                new_owner = self.get_username(deletion_order.repository_user, deletion_order.repository_name)
                if new_owner is None:
                    continue

                tasks.send_repository_deletion_notification.delay(deletion_order.id, new_owner)

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
