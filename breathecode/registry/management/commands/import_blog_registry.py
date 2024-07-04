import requests, logging, frontmatter
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from ...tasks import async_regenerate_asset_readme
from ...models import Asset, AssetCategory
from breathecode.admissions.models import Academy

logger = logging.getLogger(__name__)

HOST = "https://github.com/4GeeksAcademy/blog/blob/main"
ACADEMY_SLUG = "online"


class Command(BaseCommand):
    help = "Sync exercises and projects from old breathecode"

    def add_arguments(self, parser):
        parser.add_argument(
            "--override",
            action="store_true",
            help="Delete and add again",
        )

    def handle(self, *args, **options):

        def fetch_article(file_name):
            _resp = requests.get(f"{HOST}/blog/{file_name}?raw=true")
            if _resp.status_code == 200:
                return _resp.text

        resp = requests.get(f"{HOST}/api/posts.json?raw=true")
        if resp.status_code != 200:
            raise Exception("Error fetching article list")

        academy = Academy.objects.filter(slug=ACADEMY_SLUG).first()
        if academy is None:
            raise Exception("Academy with slug {} not found".format(ACADEMY_SLUG))

        category = {}
        category["us"] = AssetCategory.objects.filter(slug="blog-us", academy__slug=ACADEMY_SLUG).first()
        if category["us"] is None:
            category["us"] = AssetCategory(
                slug="blog-us",
                academy=academy,
                title="Blog in English",
                lang="us",
            )
            category["us"].save()

        category["es"] = AssetCategory.objects.filter(slug="blog-es", academy__slug=ACADEMY_SLUG).first()
        if category["es"] is None:
            category["es"] = AssetCategory(
                slug="blog-es",
                academy=academy,
                title="Blog en Español",
                lang="es",
            )
            category["es"].save()

        all_posts = []
        try:
            all_posts = resp.json()
            logger.debug(f"Found {len(all_posts)} posts to import...")
        except requests.exceptions.JSONDecodeError:
            logger.error("Error decoding json: {}".format(resp.text))

        owner = User.objects.filter(id=1).first()

        results = {"ignored": [], "created": [], "replaced": []}

        for post in all_posts:
            asset = Asset.objects.filter(slug=post["slug"]).first()
            if asset is None:
                asset = Asset(
                    slug=post["slug"],
                    lang=post["lang"],
                    category=category[post["lang"]],
                    academy=academy,
                    asset_type="ARTICLE",
                    status="PUBLISHED",
                    owner=owner,
                    readme_url=f"{HOST}/blog/{post['fileName']}?raw=true",
                )
                results["created"].append(asset)
                print("C", end="")
            else:
                results["replaced"].append(asset)
                print("R", end="")

            # replace title and description only
            readme = fetch_article(post["fileName"])
            asset.title = post["title"]
            asset.description = post["excerpt"] or post["subtitle"]
            asset.readme_raw = Asset.encode(readme)

            _data = frontmatter.loads(readme)
            _frontmatter = _data.metadata

            if "author" in _frontmatter:
                if isinstance(_frontmatter["author"], list):
                    asset.authors_username = ",".join(_frontmatter["author"])
                else:
                    asset.authors_username = _frontmatter["author"]

            asset.save()
            async_regenerate_asset_readme.delay(asset.slug)

        print(
            f"Done: {len(results['ignored'])} ignored, {len(results['replaced'])} replaced and {len(results['created'])} created"
        )

        for _a in results["ignored"]:
            print("Ignored: {}".format(_a.slug))

        print("Following posts replaced the description, title and authors_username")
        for _a in results["replaced"]:
            print("Replaced: {}".format(_a.slug))
