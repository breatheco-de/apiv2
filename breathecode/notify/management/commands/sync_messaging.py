import os
from django.core.management.base import BaseCommand
from ...models import SlackTeam
from ...tasks import async_slack_team_users, async_slack_team_channel

HOST = os.environ.get("OLD_BREATHECODE_API")
DATETIME_FORMAT = "%Y-%m-%d"


class Command(BaseCommand):
    help = "Sync academies from old breathecode"

    def add_arguments(self, parser):
        parser.add_argument("entity", type=str)
        parser.add_argument(
            "--cohorts",
            type=str,
            default=None,
            help="Cohorts slugs to sync",
        )
        parser.add_argument(
            "--students",
            type=str,
            default=None,
            help="Cohorts slugs to sync",
        )
        parser.add_argument("--limit", action="store", dest="limit", type=int, default=0, help="How many to import")

    def handle(self, *args, **options):
        try:
            func = getattr(self, options["entity"], "entity_not_found")
        except TypeError:
            print(f'Sync method for {options["entity"]} no Found!')
        func(options)

    def slack_users(self, options):
        teams = SlackTeam.objects.all()
        for team in teams:
            async_slack_team_users.delay(team.id)

    def slack_channels(self, options):

        teams = SlackTeam.objects.all()
        for team in teams:
            async_slack_team_channel.delay(team.id)
