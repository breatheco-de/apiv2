import logging
from breathecode.utils import APIException
from .models import Asset, AssetTranslation, AssetTechnology, AssetAlias

logger = logging.getLogger(__name__)


def create_asset(data, asset_type):
    slug = data["slug"]

    aa = AssetAlias.objects.filter(slug=slug).first()
    if aa is not None:
        raise APIException("Asset with this alias "+slug+" alrady exists")

    a = Asset.objects.filter(slug=slug).first()
    if a is None:
        a = Asset(
            slug=slug,
            asset_type=asset_type
        )
        logger.debug(f"Adding asset project {a.slug}")
    else:
        logger.debug(f"Updating asset project {slug}")

    a.title = data['title']
    a.url = data['repository']
    a.readme_url = data['readme']
    
    if "translations" in data:
        for lan in data["translations"]:
            if lan == "en":
                lan = "us" # english is really USA
            l = AssetTranslation.objects.filter(slug=lan).first()
            if l is not None: 
                if a.translations.filter(slug=lan).first() is None:
                    a.translations.add(l)
            else:
                logger.debug(f"Ignoring language {lan} because its not added as a possible AssetTranslation")

    if "intro" in data:
        a.intro_video_url = data['intro']
    if "language" in data:
        a.lang = data['language']
    if "description" in data:
        a.description = data['description']
    if "duration" in data:
        a.duration = data['duration']
    if "solution_url" in data:
        a.duration = data['solution']
    if "difficulty" in data:
        a.difficulty = data['difficulty']
    if "graded" in data:
        a.graded = data['graded']
    if "preview" in data:
        a.preview = data['preview']
    if "video-solutions" in data:
        a.with_solutions = data['video-solutions']

    a.save()
    
    aa = AssetAlias(slug=slug, asset=a)
    aa.save()