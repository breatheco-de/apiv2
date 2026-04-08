"""
Nightly (or on-demand) reconciliation of GitHub Copilot seats vs GithubAcademyUser (SYNCHED + ADD).

ORM receivers do not run for raw SQL / psql / QuerySet.update() on Heroku Postgres; this command
grants missing seats and revokes disallowed ones so manual DB edits still converge.

Heroku Scheduler example (run after business hours):
  python manage.py reconcile_github_copilot_seats

Related automation (auto-remove org members for inactive cohort users — enable on Heroku if not already):
  1) python manage.py delete_expired_githubusers
  2) python manage.py sync_github_organization

The github_owner user PAT/OAuth token must include admin:org or manage_billing:copilot for Copilot API calls.
Copilot seat removal may remain "pending cancellation" until the GitHub billing cycle ends.

See: https://docs.github.com/en/rest/copilot/copilot-user-management
"""

from django.core.management.base import BaseCommand

from breathecode.authenticate.actions import distinct_github_org_logins, reconcile_copilot_seats_for_org


class Command(BaseCommand):
    help = (
        "Sync Copilot seats with GithubAcademyUser SYNCHED+ADD: add missing API seats, remove orphans "
        "(covers DB changes that skip Django save/signals)."
    )

    def handle(self, *args, **options):
        orgs = distinct_github_org_logins()
        if not orgs:
            self.stdout.write("No AcademyAuthSettings with github_username; nothing to do.")
            return

        for org_login in orgs:
            self.stdout.write(f"Reconciling Copilot seats for org: {org_login}")
            try:
                stats = reconcile_copilot_seats_for_org(org_login)
                if stats.get("skipped"):
                    self.stdout.write(self.style.WARNING(f"  Skipped: {stats.get('reason')}"))
                else:
                    self.stdout.write(
                        f"  allowed={stats['allowed_count']} api_seats={stats['seat_count']} "
                        f"to_add={len(stats['added_usernames'])} add_batches={stats['add_batches']} "
                        f"to_remove={len(stats['removed_usernames'])} remove_batches={stats['remove_batches']}"
                    )
                    if stats["added_usernames"]:
                        self.stdout.write(f"  added logins: {','.join(stats['added_usernames'])}")
                    if stats["removed_usernames"]:
                        self.stdout.write(f"  removed logins: {','.join(stats['removed_usernames'])}")
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"  Error for {org_login}: {e}"))
