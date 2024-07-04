import os, re, logging
from random import randint
from django.core.management.base import BaseCommand
from ...actions import delete_tokens
from ...models import Profile

logger = logging.getLogger(__name__)

API_URL = os.getenv("API_URL", "")
HOST = os.environ.get("OLD_BREATHECODE_API")
DATETIME_FORMAT = "%Y-%m-%d"


class Command(BaseCommand):
    help = "Commands for authenticate app"

    def add_arguments(self, parser):
        parser.add_argument("command", type=str)
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
            func = getattr(self, options["command"], "command_not_found")
        except TypeError:
            print(f'Command method for {options["command"]} no Found!')
        func(options)

    def clean_expired_tokens(self, options):
        count = delete_tokens()
        print(f"{count} tokens were deleted")

    def sanitize_profiles(self, options):
        profile = Profile.objects.all()

        for p in profile:
            logger.debug("Sanitizing " + p.user.email)
            if p.avatar_url is None or p.avatar_url == "":
                avatar_number = randint(1, 21)
                p.avatar_url = API_URL + f"/static/img/avatar-{avatar_number}.png"

            if p.github_username is None:
                p.github_username = ""
            else:
                matches = re.findall(r"github.com\/(\w+)", p.github_username)
                if len(matches) > 0:
                    p.github_username = matches[0]

            p.save()
