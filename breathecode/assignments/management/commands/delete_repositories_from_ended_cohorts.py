import logging
import re
from datetime import datetime, timezone
from typing import Optional

from django.core.management.base import BaseCommand
from django.db.models import Q, QuerySet

from breathecode.admissions.models import Cohort
from breathecode.assignments.models import RepositoryWhiteList, Task
from breathecode.authenticate.models import AcademyAuthSettings
from breathecode.registry.models import Asset
from breathecode.services.github import Github

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Delete repositories from GitHub organization for cohorts that ended in 2023"

    # GitHub URL pattern to extract owner and repository name
    github_url_pattern = re.compile(r"https?://github\.com/(?P<user>[^/\s]+)/(?P<repo>[^/\s]+)/?")

    # Only process repositories owned by these organizations
    allowed_organizations = ["4GeeksAcademy", "4geeksacademy"]

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size", type=int, default=50, help="Number of repositories to process in each batch (default: 50)"
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Show what would be deleted without actually deleting"
        )
        parser.add_argument(
            "--year", type=int, default=2023, help="Year to filter cohorts by ending date (default: 2023)"
        )
        parser.add_argument(
            "--max-deletions", type=int, default=100, help="Maximum number of repositories to delete (default: 100)"
        )

    def handle(self, *args, **options):
        self.batch_size = options["batch_size"]
        self.dry_run = options["dry_run"]
        self.year = options["year"]
        self.max_deletions = options["max_deletions"]
        self.total_deleted = 0
        self.whitelist_cache = {}

        if self.dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE: No repositories will be deleted"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting repository deletion for cohorts ended in {self.year} "
                f"(max deletions: {self.max_deletions})"
            )
        )

        # Get eligible cohorts
        eligible_cohorts = self.get_eligible_cohorts()
        self.stdout.write(self.style.SUCCESS(f"Found {eligible_cohorts.count()} eligible cohorts"))

        # Get tasks with GitHub URLs from eligible cohorts
        tasks_with_repos = self.get_tasks_with_repositories(eligible_cohorts)
        self.stdout.write(self.style.SUCCESS(f"Found {len(tasks_with_repos)} tasks with GitHub repositories"))

        # Group tasks by GitHub organization for efficient processing
        tasks_by_org = self.group_tasks_by_organization(tasks_with_repos)

        # Process deletions for each organization
        for org_name, org_tasks in tasks_by_org.items():
            if self.total_deleted >= self.max_deletions:
                self.stdout.write(
                    self.style.WARNING(
                        f"Reached maximum deletion limit of {self.max_deletions} repositories. Stopping."
                    )
                )
                break

            deleted_count = self.process_organization_repositories(org_name, org_tasks)
            self.total_deleted += deleted_count

        self.stdout.write(
            self.style.SUCCESS(
                f"Completed! {'Would delete' if self.dry_run else 'Deleted'} {self.total_deleted} repositories"
            )
        )

    def get_eligible_cohorts(self) -> QuerySet[Cohort]:
        """Get cohorts that ended in the specified year and are eligible for repository deletion."""
        year_start = datetime(self.year, 1, 1, tzinfo=timezone.utc)
        year_end = datetime(self.year + 1, 1, 1, tzinfo=timezone.utc)

        return Cohort.objects.filter(
            stage="ENDED", ending_date__gte=year_start, ending_date__lt=year_end, never_ends=False
        ).exclude(ending_date__isnull=True)

    def get_tasks_with_repositories(self, cohorts: QuerySet[Cohort]) -> list[Task]:
        """Get all tasks with GitHub URLs from the eligible cohorts."""
        return list(
            Task.objects.filter(cohort__in=cohorts, github_url__isnull=False)
            .exclude(github_url="")
            .select_related("cohort", "user")
        )

    def group_tasks_by_organization(self, tasks: list[Task]) -> dict[str, list[Task]]:
        """Group tasks by GitHub organization for efficient processing."""
        tasks_by_org = {}

        for task in tasks:
            if not task.github_url:
                continue

            match = self.github_url_pattern.match(task.github_url)
            if not match:
                logger.warning(f"Invalid GitHub URL format: {task.github_url}")
                continue

            owner = match.group("user")

            # Only process repositories from allowed organizations
            if owner not in self.allowed_organizations:
                logger.debug(f"Skipping repository from non-allowed organization: {owner}")
                continue

            if owner not in tasks_by_org:
                tasks_by_org[owner] = []
            tasks_by_org[owner].append(task)

        return tasks_by_org

    def process_organization_repositories(self, org_name: str, tasks: list[Task]) -> int:
        """Process repository deletions for a specific GitHub organization."""
        self.stdout.write(self.style.SUCCESS(f"Processing {len(tasks)} repositories for organization: {org_name}"))

        # Get GitHub credentials for the organization
        github_client = self.get_github_client(org_name)
        if not github_client:
            self.stdout.write(self.style.ERROR(f"No GitHub credentials found for organization: {org_name}"))
            return 0

        # Extract unique repositories to avoid duplicates
        repositories = self.extract_unique_repositories(tasks)
        self.stdout.write(self.style.SUCCESS(f"Found {len(repositories)} unique repositories to process"))

        remaining_limit = self.max_deletions - self.total_deleted
        if remaining_limit <= 0:
            self.stdout.write(self.style.WARNING("Reached maximum deletion limit. Skipping organization."))
            return 0

        candidates_to_delete = []
        skipped_protected = 0
        for owner, repo_name in repositories:
            if self.should_delete_repository(owner, repo_name):
                candidates_to_delete.append((owner, repo_name))
            else:
                skipped_protected += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Eligible to delete: {len(candidates_to_delete)} "
                f"(skipped by whitelist/assets: {skipped_protected})"
            )
        )

        if len(candidates_to_delete) == 0:
            self.stdout.write(self.style.WARNING("No eligible repositories for deletion in this organization."))
            return 0

        if self.dry_run:
            preview_count = min(len(candidates_to_delete), remaining_limit)
            for owner, repo_name in candidates_to_delete[:preview_count]:
                self.stdout.write(self.style.WARNING(f"[DRY RUN] Would delete repository: {owner}/{repo_name}"))

            omitted = len(candidates_to_delete) - preview_count
            if omitted > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"[DRY RUN] Omitted {omitted} additional eligible repositories due to max-deletions limit."
                    )
                )

            return preview_count

        confirm = input(
            "Are you sure you want to delete these repositories? "
            f"(target real deletions: {remaining_limit}, candidates: {len(candidates_to_delete)}) (y/n): "
        )
        if confirm.lower() != "y":
            self.stdout.write(self.style.ERROR("Operation cancelled by user."))
            return 0

        stats = {"attempted": 0, "deleted": 0, "missing_or_inaccessible": 0, "failed": 0}
        stale_examples = []
        max_examples = 10
        progress_step = max(1, self.batch_size)

        for owner, repo_name in candidates_to_delete:
            if stats["deleted"] >= remaining_limit:
                break

            result = self.delete_repository(github_client, owner, repo_name)
            stats["attempted"] += 1

            if result == "deleted":
                stats["deleted"] += 1
            elif result == "missing_or_inaccessible":
                stats["missing_or_inaccessible"] += 1
                if len(stale_examples) < max_examples:
                    stale_examples.append(f"{owner}/{repo_name}")
            else:
                stats["failed"] += 1

            if stats["attempted"] % progress_step == 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"Progress: attempted={stats['attempted']}, deleted={stats['deleted']}, "
                        f"missing_or_inaccessible={stats['missing_or_inaccessible']}, failed={stats['failed']}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Deletion summary: "
                f"attempted={stats['attempted']}, deleted={stats['deleted']}, "
                f"missing_or_inaccessible={stats['missing_or_inaccessible']}, failed={stats['failed']}"
            )
        )

        if stale_examples:
            self.stdout.write(
                self.style.WARNING(
                    "Examples of stale DB references (repo missing or inaccessible on GitHub): "
                    + ", ".join(stale_examples)
                )
            )

        if stats["deleted"] < remaining_limit and stats["attempted"] == len(candidates_to_delete):
            self.stdout.write(
                self.style.WARNING(
                    "Could not reach target real deletions because there are no more eligible candidates."
                )
            )

        return stats["deleted"]

    def get_github_client(self, org_name: str) -> Optional[Github]:
        """Get GitHub client for the specified organization."""
        try:
            settings = AcademyAuthSettings.objects.filter(
                github_username__iexact=org_name,
                github_owner__isnull=False,
                github_owner__credentialsgithub__isnull=False,
            ).first()

            if not settings:
                return None

            return Github(org=org_name, token=settings.github_owner.credentialsgithub.token)
        except Exception as e:
            logger.error(f"Error getting GitHub client for {org_name}: {str(e)}")
            return None

    def extract_unique_repositories(self, tasks: list[Task]) -> list[tuple[str, str]]:
        """Extract unique repository names from tasks."""
        repositories = set()

        for task in tasks:
            match = self.github_url_pattern.match(task.github_url)
            if match:
                owner = match.group("user")
                repo = match.group("repo")

                if "." in repo:
                    repo = repo.split(".")[0]

                repositories.add((owner, repo))

        return list(repositories)

    def get_whitelist_repositories(self, owner: str) -> set[str]:
        """
        Fetch whitelisted repositories for an owner once and cache in memory.
        This avoids one DB query per repository during deletion checks.
        """
        owner_key = owner.lower()
        if owner_key not in self.whitelist_cache:
            names = RepositoryWhiteList.objects.filter(
                provider="GITHUB",
                repository_user__iexact=owner,
            ).values_list("repository_name", flat=True)

            self.whitelist_cache[owner_key] = {name.lower() for name in names}

        return self.whitelist_cache[owner_key]

    def should_delete_repository(self, owner: str, repo_name: str) -> bool:
        """Check if a repository should be deleted based on whitelist and other criteria."""
        # Check whitelist from in-memory cache (loaded once per owner)
        whitelisted_repositories = self.get_whitelist_repositories(owner)
        is_whitelisted = repo_name.lower() in whitelisted_repositories

        if is_whitelisted:
            logger.info(f"Repository {owner}/{repo_name} is whitelisted, skipping deletion")
            return False

        # Check if any Asset references this repository
        repo_url_pattern = f"github.com/{owner}/{repo_name}"
        assets_using_repo = Asset.objects.filter(
            Q(url__icontains=repo_url_pattern)
            | Q(solution_url__icontains=repo_url_pattern)
            | Q(template_url__icontains=repo_url_pattern)
            | Q(readme_url__icontains=repo_url_pattern)
        ).exists()

        if assets_using_repo:
            logger.info(f"Repository {owner}/{repo_name} is referenced by Asset(s), skipping deletion")
            return False

        return True

    def delete_repository(self, github_client: Github, owner: str, repo_name: str) -> str:
        """Delete a repository using the GitHub API."""
        if self.dry_run:
            return "deleted"

        try:
            # Check if repository exists before attempting deletion
            if not github_client.repo_exists(owner, repo_name):
                logger.info(
                    f"Skipping stale repository reference, not found or inaccessible: {owner}/{repo_name}"
                )
                return "missing_or_inaccessible"

            # Delete the repository
            response = github_client.delete_org_repo(owner, repo_name)

            if response.status_code == 204:  # GitHub returns 204 for successful deletion
                self.stdout.write(self.style.SUCCESS(f"Successfully deleted repository: {owner}/{repo_name}"))
                logger.info(f"Deleted repository: {owner}/{repo_name}")
                return "deleted"
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"Failed to delete repository {owner}/{repo_name}: " f"HTTP {response.status_code}"
                    )
                )
                logger.error(f"Failed to delete repository {owner}/{repo_name}: HTTP {response.status_code}")
                return "failed"

        except Exception as e:
            error_message = str(e).strip()
            if not error_message:
                error_message = "Unknown error returned by GitHub API"

            low_error_message = error_message.lower()
            if "404" in low_error_message or "not found" in low_error_message:
                logger.info(
                    f"Skipping stale repository reference, not found or inaccessible: {owner}/{repo_name}"
                )
                return "missing_or_inaccessible"

            self.stdout.write(self.style.ERROR(f"Error deleting repository {owner}/{repo_name}: {error_message}"))
            logger.error(f"Error deleting repository {owner}/{repo_name}: {error_message}")
            return "failed"
