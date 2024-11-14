import hashlib
import logging
import os
import pathlib
import re
from typing import Optional

import requests
from bs4 import BeautifulSoup
from celery import shared_task
from circuitbreaker import CircuitBreakerError
from django.db.models.query_utils import Q
from django.utils import timezone
from github import Github
from task_manager.core.exceptions import AbortTask, RetryTask
from task_manager.django.decorators import task

from breathecode.admissions.models import SyllabusVersion
from breathecode.assessment.models import Assessment
from breathecode.authenticate.models import CredentialsGithub
from breathecode.media.models import Media, MediaResolution
from breathecode.media.views import media_gallery_bucket
from breathecode.monitoring.decorators import WebhookTask
from breathecode.services.google_cloud import FunctionV1
from breathecode.services.google_cloud.storage import Storage
from breathecode.services.seo import SEOAnalyzer
from breathecode.utils.decorators import TaskPriority
from breathecode.utils.views import set_query_parameter

from .actions import (
    add_syllabus_translations,
    asset_images_bucket,
    clean_asset_readme,
    generate_screenshot,
    pull_from_github,
    pull_repo_dependencies,
    screenshots_bucket,
    test_asset,
    upload_image_to_bucket,
)
from .models import Asset, AssetImage, AssetContext

logger = logging.getLogger(__name__)


def google_project_id():
    return os.getenv("GOOGLE_PROJECT_ID", "")


img_regex = r"https?:(?:[/|.|\w|\s|-])*\.(?:jpg|gif|png|svg|jpeg)"


def is_remote_image(_str):
    if _str is None or _str == "" or asset_images_bucket("") in _str:
        return False

    match = re.search(img_regex, _str)
    if match is None:
        return False

    return True


@shared_task(priority=TaskPriority.ACADEMY.value)
def async_pull_from_github(asset_slug, user_id=None, override_meta=False):
    logger.debug(f"Synching asset {asset_slug} with data found on github")
    asset_or_status = pull_from_github(asset_slug, override_meta=override_meta)
    if asset_or_status != "ERROR":
        async_pull_project_dependencies.delay(asset_slug)

    return asset_or_status != "ERROR"


@shared_task(priority=TaskPriority.ACADEMY.value)
def async_pull_project_dependencies(asset_slug):

    asset = Asset.objects.filter(slug=asset_slug).first()
    try:
        if asset.asset_type not in ["PROJECT", "STARTER"]:
            raise Exception(
                f"Asset {asset_slug} is not a project or starter, only projects or starters can have dependencies"
            )

        target_asset = asset
        if asset.template_url is not None and asset.template_url != "":
            target_asset = Asset.get_by_github_url(asset.template_url)
            if target_asset is None:
                raise Exception(
                    f"Asset {asset_slug} template {asset.template_url} not found in the database as another asset"
                )
            if target_asset.asset_type != "STARTER":
                target_asset.log_error(
                    "not-a-template",
                    f"Asset {asset_slug} references {target_asset.slug} as a template but its type != 'STARTER'",
                )
            target_asset.save()
        logger.debug(f"Retrieving asset dependencies for {asset_slug}")

        if target_asset.owner is None:
            raise Exception(f"Asset {asset_slug} needs to have an owner in order to retrieve its github dependencies")

        credentials = CredentialsGithub.objects.filter(user__id=target_asset.owner.id).first()
        if credentials is None:
            raise Exception(
                f"Github credentials for user {target_asset.owner.first_name} {target_asset.owner.last_name} (id: {target_asset.owner.id}) not found when retrieving asset {asset_slug} dependencies"
            )

        g = Github(credentials.token)

        dependency_string = pull_repo_dependencies(g, target_asset)
        target_asset.dependencies = dependency_string
        target_asset.save()
        if target_asset.id != asset.id:
            asset.dependencies = dependency_string
            asset.save()
        return True
    except Exception:
        logger.exception(f"Error retrieving dependencies for asset {asset.slug}")
        return False


@shared_task(priority=TaskPriority.ACADEMY.value)
def async_test_asset(asset_slug):
    a = Asset.objects.filter(slug=asset_slug).first()
    if a is None:
        logger.debug(f"Error: Error testing asset with slug {asset_slug}, does not exist.")

    try:
        if test_asset(a):
            return True
    except Exception:
        logger.exception(f"Error testing asset {a.slug}")

    return False


@shared_task(priority=TaskPriority.ACADEMY.value)
def async_update_frontend_asset_cache(asset_slug):
    try:
        if os.getenv("ENV", "") != "production":
            return

        logger.info("async_update_frontend_asset_cache")
        url = os.getenv("APP_URL", "") + f"/api/asset/{asset_slug}"
        requests.put(url=url)
    except Exception as e:
        logger.error(str(e))


@shared_task(priority=TaskPriority.ACADEMY.value)
def async_regenerate_asset_readme(asset_slug):
    a = Asset.objects.filter(slug=asset_slug).first()
    if a is None:
        logger.debug(f"Error: Error running SEO report for asset with slug {asset_slug}, does not exist.")
        return False

    a.readme = a.readme_raw
    a.save()
    clean_asset_readme(a)

    async_download_readme_images.delay(a.slug)
    async_update_frontend_asset_cache.delay(a.slug)

    return a.cleaning_status == "OK"


@shared_task(priority=TaskPriority.ACADEMY.value)
def async_execute_seo_report(asset_slug):
    a = Asset.objects.filter(slug=asset_slug).first()
    if a is None:
        logger.debug(f"Error: Error running SEO report for asset with slug {asset_slug}, does not exist.")

    try:
        report = SEOAnalyzer(a)
        report.start()
    except Exception:
        logger.exception(f"Error running SEO report asset {a.slug}")

    return False


@task(priority=TaskPriority.ACADEMY.value)
def async_create_asset_thumbnail_legacy(asset_slug: str, **_):
    from breathecode.registry.actions import AssetThumbnailGenerator

    asset = Asset.objects.filter(slug=asset_slug).first()
    if asset is None:
        raise Exception(f"Asset with slug {asset_slug} not found")

    generator = AssetThumbnailGenerator(asset)
    generator.create()

    return True


@task(priority=TaskPriority.ACADEMY.value)
def async_create_asset_thumbnail(asset_slug: str, **_):

    asset = Asset.objects.filter(slug=asset_slug).first()
    if asset is None:
        raise RetryTask(f"Asset with slug {asset_slug} not found")

    preview_url = asset.get_preview_generation_url()
    if preview_url is None:
        raise AbortTask("Not able to retrieve a preview generation")

    name = asset.get_thumbnail_name()
    url = set_query_parameter(preview_url, "slug", asset_slug)

    response = None
    logger.info(f"Generating screenshot for {preview_url}")
    try:
        response = generate_screenshot(url, "1200x630", delay=1000)

    except Exception as e:
        raise AbortTask("Error calling service to generate thumbnail screenshot: " + str(e))

    if response.status_code >= 400:
        raise AbortTask(
            "Unhandled error with async_create_asset_thumbnail, the cloud function `screenshots` "
            f"returns status code {response.status_code}"
        )

    file = response.content

    hash = hashlib.sha256(file).hexdigest()
    content_type = response.headers["content-type"]

    storage = Storage()

    cloud_file = storage.file(screenshots_bucket(), hash)

    cloud_file.upload(file, content_type=content_type)
    url = cloud_file.url()

    # file already exists for this academy
    media = Media.objects.filter(hash=hash, academy=asset.academy).first()
    if media is not None:

        if asset.preview is None or asset.preview == "":
            asset.preview = media.url
            asset.save()

        raise AbortTask(f"Media with hash {hash} already exists, skipping")

    # file already exists for another academy
    media = Media.objects.filter(hash=hash).first()
    if media:

        media = Media(
            slug=name.split(".")[0],
            name=media.name,
            url=media.url,
            thumbnail=media.thumbnail,
            academy=asset.academy,
            mime=media.mime,
            hash=media.hash,
        )
        media.save()

        if asset.preview is None or asset.preview == "":
            asset.preview = media.url
            asset.save()

        raise AbortTask(f"Media was save with {hash} for academy {asset.academy}")

    # if media does not exist too, keep the screenshots with other name
    cloud_file.rename(hash)
    url = f"https://storage.googleapis.com/{screenshots_bucket()}/{hash}"

    media = Media(
        slug=name.split(".")[0],
        name=name,
        url=url,
        thumbnail=f"{url}-thumbnail",
        academy=asset.academy,
        mime="image/png",  # this should change in a future, check the cloud function
        hash=hash,
    )
    media.save()

    if asset.preview is None or asset.preview == "":
        asset.preview = url
        asset.save()

    logger.warning(f"Media was save with {hash} for academy {asset.academy}")


@shared_task(priority=TaskPriority.ACADEMY.value)
def async_download_readme_images(asset_slug):
    logger.debug(f"Downloading images for asset {asset_slug}")

    asset = Asset.get_by_slug(asset_slug)
    if asset is None:
        raise Exception(f"Asset with slug {asset_slug} not found")

    readme = asset.get_readme(parse=True)
    if "html" not in readme:
        logger.error(f"Asset with {asset_slug} readme cannot be parse into an HTML")
        return False

    images = BeautifulSoup(readme["html"], features="html.parser").find_all("img", attrs={"srcset": True})

    # check if old images are stil in the new markdown file
    old_images = asset.images.all()
    no_longer_used = {}
    for img in old_images:
        # we will assume they are not by default
        no_longer_used[img.original_url] = img

    image_links = []
    for image in images:
        image_links.append(image["src"])

        srcset = image.attrs.get("srcset")
        if srcset and srcset != "":
            srcsets = [src.strip().split(" ")[0] for src in srcset.split(",")]
            image_links += srcsets

    additional_img_urls = list(re.finditer(img_regex, readme["html"]))
    while len(additional_img_urls) > 0:
        match = additional_img_urls.pop(0)
        if match is not None:
            img_url = match.group()
            image_links.append(img_url)

    image_links = list(dict.fromkeys(filter(lambda x: is_remote_image(x), image_links)))
    logger.debug(f"Found {len(image_links)} images on asset {asset_slug}")

    # create subfolder with the page name
    if len(image_links) == 0:
        print("No images found")
        return False

    for link in image_links:
        if link in no_longer_used:
            del no_longer_used[link]
        async_download_single_readme_image.delay(asset_slug, link)

    # delete asset from this image
    logger.debug(f"Found {len(no_longer_used)} images no longer used on asset {asset_slug}")
    for old_img in no_longer_used:
        no_longer_used[old_img].assets.remove(asset)

        # if its not being sed on any other asset, we delete it from cloud
        if no_longer_used[old_img].assets.count() == 0:
            async_remove_img_from_cloud(no_longer_used[old_img].id)

    return True


@task(priority=TaskPriority.ACADEMY.value)
def async_delete_asset_images(asset_slug, **_):

    asset = Asset.get_by_slug(asset_slug)
    if asset is None:
        raise RetryTask(f"Asset with slug {asset_slug} not found")

    storage = Storage()
    for img in asset.images.all():
        if img.assets.count() == 1 and img.asset.filter(slug=asset_slug).exists():
            extension = pathlib.Path(img.name).suffix
            cloud_file = storage.file(asset_images_bucket(), img.hash + extension)
            cloud_file.delete()
            img.delete()
        else:
            img.assets.remove(asset)

        logger.info(f"Image {img.name} was deleted")

    return True


@task(priority=TaskPriority.ACADEMY.value)
def async_remove_img_from_cloud(id, **_):

    logger.info("async_remove_img_from_cloud")

    img = AssetImage.objects.filter(id=id).first()
    if img is None:
        raise RetryTask(f"Image with id {id} not found")

    img_name = img.name

    storage = Storage()
    extension = pathlib.Path(img.name).suffix
    cloud_file = storage.file(asset_images_bucket(), img.hash + extension)
    cloud_file.delete()
    img.delete()

    logger.info(f"Image id ({img_name}) was deleted from the cloud")
    return True


@task(priority=TaskPriority.ACADEMY.value)
def async_remove_asset_preview_from_cloud(hash, **_):

    logger.info("async_remove_asset_preview_from_cloud")

    media = Media.objects.filter(hash=hash).first()
    if media is None:
        raise Exception(f"Media with hash {hash} not found")

    media_name = media.name

    storage = Storage()
    extension = media.mime.split("/")[-1]
    cloud_file = storage.file(screenshots_bucket(), media.hash + extension)
    cloud_file.delete()
    media.delete()

    logger.info(f"Media name ({media_name}) was deleted from the cloud")
    return True


@task(priority=TaskPriority.ACADEMY.value)
def async_upload_image_to_bucket(id, **_):

    img = AssetImage.objects.filter(id=id).first()
    if img is None:
        raise Exception(f"Image with id {id} not found")

    img.download_status = "PENDING"
    # FIXME: undefined variable
    img.download_details = f"Downloading {img.original_url}"
    img.save()

    try:
        img = upload_image_to_bucket(img)

    except CircuitBreakerError as e:
        raise e

    except Exception as e:
        img.download_details = str(e)
        img.download_status = "ERROR"
        raise e

    img.save()
    return img.download_status


@task(priority=TaskPriority.ACADEMY.value)
def async_download_single_readme_image(asset_slug, link, **_):

    asset = Asset.get_by_slug(asset_slug)
    if asset is None:
        raise RetryTask(f"Asset with slug {asset_slug} not found")

    img = AssetImage.objects.filter(Q(original_url=link) | Q(bucket_url=link)).first()
    if img is None:
        temp_filename = link.split("/")[-1].split("?")[0]
        img = AssetImage(name=temp_filename, original_url=link, last_download_at=timezone.now())

    if img.download_status != "OK":

        img.download_status = "PENDING"
        img.download_details = f"Downloading {link}"
        img.save()

        try:
            img = upload_image_to_bucket(img, asset)

        except CircuitBreakerError as e:
            raise e

        except Exception as e:
            img.download_details = str(e)
            img.download_status = "ERROR"
            img.save()
            raise e

    img.save()
    readme = asset.get_readme()
    asset.set_readme(readme["decoded"].replace(link, img.bucket_url))
    asset.save()
    return img.download_status


@shared_task(priority=TaskPriority.ACADEMY.value)
def async_resize_asset_thumbnail(media_id: int, width: Optional[int] = 0, height: Optional[int] = 0):
    media = Media.objects.filter(id=media_id).first()
    if media is None:
        logger.error(f"Media with id {media_id} not found")
        return

    if not width and not height:
        logger.error("async_resize_asset_thumbnail needs the width or height parameter")
        return

    if width and height:
        logger.error("async_resize_asset_thumbnail can't be used with width and height together")
        return

    kwargs = {"width": width} if width else {"height": height}

    func = FunctionV1(region="us-central1", project_id=google_project_id(), name="resize-image")

    response = func.call(
        {
            **kwargs,
            "filename": media.hash,
            "bucket": media_gallery_bucket(),
        }
    )

    res = response.json()

    if not res["status_code"] == 200 or not res["message"] == "Ok":
        logger.error(f"Unhandled error with `resize-image` cloud function, response {res}")
        return

    resolution = MediaResolution(width=res["width"], height=res["height"], hash=media.hash)
    resolution.save()


@shared_task(bind=True, base=WebhookTask, priority=TaskPriority.CONTENT.value)
def async_synchonize_repository_content(self, webhook, override_meta=True):

    logger.debug("async_synchonize_repository_content")
    payload = webhook.get_payload()

    # some times the json contains a nested payload property
    if "payload" in payload:
        payload = payload["payload"]

    if "commits" not in payload:
        raise AbortTask("No commits found on the push object")

    if "repository" not in payload:
        raise AbortTask("Missing repository information")
    elif "url" not in payload["repository"]:
        raise AbortTask(
            'Repository payload is invalid, expecting an object with "url" key. Check the webhook content-type'
        )

    base_repo_url = payload["repository"]["url"]
    default_branch = payload["repository"]["default_branch"]

    files = []
    for commit in payload["commits"]:
        for file_path in commit["modified"]:
            # one file can be modified in multiple commits, but we don't have to synch many times
            if file_path not in files:
                files.append(file_path)
                logger.debug(
                    f"The file {file_path} was modified, searching for matches in our registry with {base_repo_url}/blob/{default_branch}/{file_path}"
                )

                # include readme files and quiz json files
                all_readme_files = Q(readme_url__icontains=f"{base_repo_url}/blob/{default_branch}/{file_path}")

                # Conditional query for when 'learn.json' is in file_path
                learn_json_files = (
                    Q(
                        asset_type__in=["EXERCISE", "PROJECT"],
                        readme_url__icontains=f"{base_repo_url}/blob/{default_branch}/",
                    )
                    if "learn.json" in file_path
                    else Q()
                )

                # Execute the combined query
                assets = Asset.objects.filter(all_readme_files | learn_json_files)
                for a in assets:
                    if commit["id"] == a.github_commit_hash:
                        # ignore asset because the commit content is already on the asset
                        # probably the asset was updated in github using the breathecode api
                        continue
                    logger.debug(f"Pulling asset from github for asset: {a.slug}")
                    async_pull_from_github.delay(a.slug, override_meta)

    return webhook


@shared_task(priority=TaskPriority.BACKGROUND.value)
def async_add_syllabus_translations(syllabus_slug, version):

    syllabus_version = SyllabusVersion.objects.filter(syllabus__slug=syllabus_slug, version=version).first()
    if syllabus_version is None:
        raise Exception(f'Syllabus {syllabus_slug} with version "{version}" not found')

    if syllabus_version.json is None:
        syllabus_version.json = {"days": []}

    syllabus_version.json = add_syllabus_translations(syllabus_version.json)
    syllabus_version.save()


@shared_task(priority=TaskPriority.BACKGROUND.value)
def async_generate_quiz_config(assessment_id):

    assessment = Assessment.objects.filter(id=assessment_id, is_archived=False).first()
    if assessment is None:
        raise Exception(f"Assessment {assessment_id} not found or its archived")

    assets = assessment.asset_set.all()
    for a in assets:
        a.config = a.generate_quiz_json()
        a.save()

    return True


@shared_task(priority=TaskPriority.CONTENT.value)
def async_build_asset_context(asset_id):
    asset = Asset.objects.get(id=asset_id)
    LANG_MAP = {
        "en": "english",
        "es": "spanish",
        "it": "italian",
    }

    lang = asset.lang or asset.category.lang
    lang_name = LANG_MAP.get(lang, lang)

    context = f"This {asset.asset_type} about {asset.title} is written in {lang_name}. "

    translations = ", ".join([x.title for x in asset.all_translations.all()])
    if translations:
        context = context[:-2]
        context += f", and it has the following translations: {translations}. "

    if asset.solution_url:
        context = context[:-2]
        context += f", and it has a solution code this link is: {asset.solution_url}. "

    if asset.solution_video_url:
        context = context[:-2]
        context += f", and it has a video solution this link is {asset.solution_video_url}. "

    context += f"It's category related is (what type of skills the student will get) {asset.category.title}. "

    technologies = ", ".join([x.title for x in asset.technologies.filter(Q(lang=lang) | Q(lang=None))])
    if technologies:
        context += f"This asset is about the following technologies: {technologies}. "

    if asset.external:
        context += "This asset is external, which means it opens outside 4geeks. "

    if asset.interactive:
        context += "This asset opens on LearnPack so it has a step-by-step of the exercises that you should follow. "

    if asset.gitpod:
        context += (
            f"This {asset.asset_type} can be opened both locally or with click and code (This "
            "way you don't have to install anything and it will open automatically on gitpod or github codespaces). "
        )

    if asset.interactive == True and asset.with_video == True:
        context += f"This {asset.asset_type} has videos on each step. "

    if asset.interactive == True and asset.with_solutions == True:
        context += f"This {asset.asset_type} has a code solution on each step. "

    if asset.duration:
        context += f"This {asset.asset_type} will last {asset.duration} hours. "

    if asset.difficulty:
        context += f"Its difficulty is considered as {asset.difficulty}. "

    if asset.superseded_by and asset.superseded_by.title != asset.title:
        context += f"This {asset.asset_type} has a previous version which is: {asset.superseded_by.title}. "

    if asset.asset_type == "PROJECT" and not asset.delivery_instructions:
        context += "This project should be delivered by sending a github repository URL. "

    if asset.asset_type == "PROJECT" and asset.delivery_instructions and asset.delivery_formats:
        context += (
            f"This project should be delivered by adding a file of one of these types: {asset.delivery_formats}. "
        )

    if asset.asset_type == "PROJECT" and asset.delivery_regex_url:
        context += f"This project should be delivered with a URL that follows this format: {asset.delivery_regex_url}. "

    assets_related = ", ".join([x.slug for x in asset.assets_related.all()])
    if assets_related:
        context += (
            f"In case you still need to learn more about the basics of this {asset.asset_type}, "
            "you can check these lessons, and exercises, "
            f"and related projects to get ready for this content: {assets_related}. "
        )

    if asset.html:
        context += "The markdown file with "

        if asset.asset_type == "PROJECT":
            context += "the instructions"
        else:
            context += "the content"

        context += f" of this {asset.asset_type} is the following: {asset.html}."

    AssetContext.objects.update_or_create(asset=asset, defaults={"ai_context": context, "status": "DONE"})
