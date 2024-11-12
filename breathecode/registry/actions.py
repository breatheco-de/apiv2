import base64
import hashlib
import json
import logging
import os
import pathlib
import re
from typing import Optional
from urllib.parse import urlencode

import requests
from django.db.models import Q
from django.template.loader import get_template
from django.utils import timezone
from github import Github

from breathecode.assessment.actions import create_from_asset
from breathecode.authenticate.models import CredentialsGithub
from breathecode.media.models import Media, MediaResolution
from breathecode.services.google_cloud.storage import Storage
from breathecode.utils.views import set_query_parameter

from .models import ASSET_STATUS, Asset, AssetErrorLog, AssetImage, AssetTechnology, ContentVariable, OriginalityScan
from .serializers import AssetBigSerializer
from .utils import (
    ArticleValidator,
    AssetException,
    ExerciseValidator,
    LessonValidator,
    OriginalityWrapper,
    ProjectValidator,
    QuizValidator,
)

logger = logging.getLogger(__name__)

ASSET_STATUS_DICT = [x for x, y in ASSET_STATUS]


# remove markdown elemnts from text and return the clean text output only
def unmark(text):

    from io import StringIO

    from markdown import Markdown

    def unmark_element(element, stream=None):
        if stream is None:
            stream = StringIO()
        if element.text:
            stream.write(element.text)
        for sub in element:
            unmark_element(sub, stream)
        if element.tail:
            stream.write(element.tail)
        return stream.getvalue()

    # patching Markdown
    Markdown.output_formats["plain"] = unmark_element
    __md = Markdown(output_format="plain")
    __md.stripTopLevelTags = False

    return __md.convert(text)


def allowed_mimes():
    return ["image/png", "image/svg+xml", "image/jpeg", "image/gif", "image/jpg"]


def asset_images_bucket(default=None):
    return os.getenv("ASSET_IMAGES_BUCKET", default)


def generate_external_readme(a):

    if not a.external:
        return False

    readme_lang = a.lang.lower()

    if readme_lang == "us":
        readme = get_template("external.md")
    else:
        readme = get_template(f"external.{readme_lang}.md")
    a.set_readme(readme.render(AssetBigSerializer(a).data))
    a.save()
    return True


def get_video_url(video_id):
    if re.search(r"https?:\/\/", video_id) is None:
        return "https://www.youtube.com/watch?v=" + video_id
    else:
        patterns = ((r"(https?:\/\/www\.loom\.com\/)embed(\/.+)", r"\1share\2"),)
        for regex, replacement in patterns:
            video_id = re.sub(regex, replacement, video_id)
        return video_id


def get_user_from_github_username(username):
    authors = username.split(",")
    github_users = []
    for _author in authors:
        u = CredentialsGithub.objects.filter(username=_author).first()
        if u is not None:
            github_users.append(u.user)
    return github_users


def pull_from_github(asset_slug, author_id=None, override_meta=False):

    logger.debug(f"Sync with github asset {asset_slug}")

    asset = None
    try:

        asset = Asset.objects.filter(slug=asset_slug).first()
        if asset is None:
            raise Exception(f"Asset with slug {asset_slug} not found when attempting to sync with github")

        asset.status_text = "Starting to sync..."
        asset.sync_status = "PENDING"
        asset.save()

        if generate_external_readme(asset):
            asset.status_text = "Readme file for external asset generated, not github sync"
            asset.sync_status = "OK"
            asset.last_synch_at = None
            asset.save()
            return asset.sync_status

        if asset.owner is not None:
            author_id = asset.owner.id

        if author_id is None:
            raise Exception(
                f"System does not know what github credentials to use to retrieve asset info for: {asset_slug}"
            )

        if asset.readme_url is None or "github.com" not in asset.readme_url:
            raise Exception(f"Missing or invalid URL on {asset_slug}, it does not belong to github.com")

        credentials = CredentialsGithub.objects.filter(user__id=author_id).first()
        if credentials is None:
            raise Exception(f"Github credentials for this user {author_id} not found when sync asset {asset_slug}")

        g = Github(credentials.token)
        if asset.asset_type in ["LESSON", "ARTICLE"]:
            asset = pull_github_lesson(g, asset, override_meta=override_meta)
        elif asset.asset_type in ["QUIZ"]:
            asset = pull_quiz_asset(g, asset)
        else:
            asset = pull_learnpack_asset(g, asset, override_meta=True)

        asset.status_text = "Successfully Synched"
        asset.sync_status = "OK"
        asset.last_synch_at = timezone.now()
        asset.save()
        logger.debug(f"Successfully re-synched asset {asset_slug} with github")

        return asset
    except Exception as e:
        logger.exception(e)
        message = ""
        if hasattr(e, "data") and e.data:
            message = e.data["message"]
        else:
            message = str(e).replace('"', "'")

        logger.error(f"Error updating {asset_slug} from github: " + str(message))

        # if the exception triggered too early, the asset will be early
        if asset is not None:
            asset.status_text = str(message)
            asset.sync_status = "ERROR"
            asset.save()
            return asset.sync_status

    return "ERROR"


def push_to_github(asset_slug, author=None):

    logger.debug(f"Push asset {asset_slug} to github")

    asset = None
    try:

        asset = Asset.objects.filter(slug=asset_slug).first()
        if asset is None:
            raise Exception(f"Asset with slug {asset_slug} not found when attempting github push")

        asset.status_text = "Starting to push..."
        asset.sync_status = "PENDING"
        asset.save()

        if author is None:
            author = asset.owner

        if asset.external:
            raise Exception('Asset is marked as "external" so it cannot push to github')

        if author is None:
            raise Exception("Asset must have an owner with write permissions on the repository")

        if asset.readme_url is None or "github.com" not in asset.readme_url:
            raise Exception(f"Missing or invalid URL on {asset_slug}, it does not belong to github.com")

        credentials = CredentialsGithub.objects.filter(user__id=author.id).first()
        if credentials is None:
            raise Exception(
                f"Github credentials for user {author.first_name} {author.last_name} (id: {author.id}) not found when synching asset {asset_slug}"
            )

        g = Github(credentials.token)
        asset = push_github_asset(g, asset)

        asset.status_text = "Successfully Synched"
        asset.sync_status = "OK"
        asset.last_synch_at = timezone.now()
        asset.save()
        logger.debug(f"Successfully re-synched asset {asset_slug} with github")

        return asset
    except Exception as e:
        logger.exception(e)
        message = ""
        if hasattr(e, "data"):
            message = e.data["message"]
        else:
            message = str(e).replace('"', "'")

        logger.error(f"Error updating {asset_slug} from github: " + str(message))
        # if the exception triggered too early, the asset will be early
        if asset is not None:
            asset.status_text = str(message)
            asset.sync_status = "ERROR"
            asset.save()
            return asset.sync_status

    return "ERROR"


def get_blob_content(repo, path_name, branch="main"):

    if "?" in path_name:
        path_name = path_name.split("?")[0]

    # first get the branch reference
    ref = repo.get_git_ref(f"heads/{branch}")
    # then get the tree
    tree = repo.get_git_tree(ref.object.sha, recursive="/" in path_name).tree
    # look for path in tree
    sha = [x.sha for x in tree if x.path == path_name]
    if not sha:
        # well, not found..
        return None
    # we have sha
    return repo.get_git_blob(sha[0])


def set_blob_content(repo, path_name, content, file_name, branch="main"):

    if content is None or content == "":
        raise Exception(f"Blob content is empty for {path_name}")

    # first get the branch reference
    ref = repo.get_git_ref(f"heads/{branch}")
    # then get the tree
    tree = repo.get_git_tree(ref.object.sha, recursive="/" in path_name).tree
    # look for path in tree
    file = [x for x in tree if x.path == path_name]
    if not file:
        # well, not found..
        return None

    # update
    return repo.update_file(file[0].path, f"Update {file_name}", content, file[0].sha)


def generate_screenshot(url: str, dimension: str = "1200x630", **kwargs):
    screenshot_key = os.getenv("SCREENSHOT_MACHINE_KEY", "")
    params = {
        "key": screenshot_key,
        "url": url,
        "dimension": dimension,
        **kwargs,
    }
    request = requests.request("GET", "https://api.screenshotmachine.com", params=params, timeout=8)

    return request


def push_github_asset(github, asset: Asset):

    logger.debug(f"Sync pull_github_lesson {asset.slug}")

    if asset.readme_url is None:
        raise Exception("Missing Readme URL for asset " + asset.slug + ".")

    org_name, repo_name, branch_name = asset.get_repo_meta()
    repo = github.get_repo(f"{org_name}/{repo_name}")

    file_name = os.path.basename(asset.readme_url)

    if branch_name is None:
        raise Exception("Readme URL must include branch name after blob")

    result = re.search(r"\/blob\/([\w\d_\-]+)\/(.+)", asset.readme_url)
    branch, file_path = result.groups()
    logger.debug(f"Fetching readme: {file_path}")

    decoded_readme = None
    if asset.asset_type in ["LESSON", "ARTICLE"]:
        # we commit the raw readme, we don't want images to be replaced in the original github
        decoded_readme = base64.b64decode(asset.readme_raw.encode("utf-8")).decode("utf-8")

    elif asset.asset_type == "QUIZ":
        decoded_readme = json.dumps(asset.config, indent=4)

    else:
        raise Exception(f"Assets with type {asset.asset_type} cannot be commited to Github")

    if decoded_readme is None or decoded_readme == "None" or decoded_readme == "":
        raise Exception("The content you are trying to push to Github is empty")

    result = set_blob_content(repo, file_path, decoded_readme, file_name, branch=branch)
    if "commit" in result:
        asset.github_commit_hash = result["commit"].sha

    return asset


def pull_github_lesson(github, asset: Asset, override_meta=False):

    logger.debug(f"Sync pull_github_lesson {asset.slug}")

    if asset.readme_url is None:
        raise Exception("Missing Readme URL for lesson " + asset.slug + ".")

    org_name, repo_name, branch_name = asset.get_repo_meta()
    repo = github.get_repo(f"{org_name}/{repo_name}")

    os.path.basename(asset.readme_url)

    if branch_name is None:
        raise Exception("Lesson URL must include branch name after blob")

    result = re.search(r"\/blob\/([\w\d_\-]+)\/(.+)", asset.readme_url)
    _, file_path = result.groups()
    logger.debug(f"Fetching readme: {file_path}")

    blob_file = get_blob_content(repo, file_path, branch=branch_name)
    if blob_file is None:
        raise Exception("Nothing was found under " + file_path)

    base64_readme = blob_file.content
    asset.readme_raw = base64_readme

    # this avoids to keep using the old readme file, we do have a new version
    # the asset.get_readme function will not update the asset if we keep the old version
    if asset.readme_raw is not None:
        asset.readme = asset.readme_raw

    # only the first time a lesson is synched it will override some of the properties
    readme = asset.get_readme(parse=True)
    if asset.last_synch_at is None or override_meta:
        fm = dict(readme["frontmatter"].items())
        if "slug" in fm and fm["slug"] != asset.slug:
            logger.debug(f'New slug {fm["slug"]} found for lesson {asset.slug}')
            asset.slug = fm["slug"]

        if "excerpt" in fm:
            asset.description = fm["excerpt"]
        elif "description" in fm:
            asset.description = fm["description"]
        elif "subtitle" in fm:
            asset.description = fm["subtitle"]

        if "title" in fm and fm["title"] != "":
            asset.title = fm["title"]

        def parse_boolean(value):
            true_values = {"1", "true"}
            false_values = {"0", "false"}
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, str)):
                value_str = str(value).lower()  # Convert value to string and lowercase
                if value_str in true_values:
                    return True
                elif value_str in false_values:
                    return False

            raise ValueError(f"Invalid value for boolean conversion: {value}")

        if "table_of_contents" in fm and fm["table_of_contents"] != "":
            asset.enable_table_of_content = parse_boolean(fm["table_of_contents"])

        if "video" in fm and fm["video"] != "":
            asset.intro_video_url = fm["video"]

        if "authors" in fm and fm["authors"] != "":
            asset.authors_username = ",".join(fm["authors"])

        # retrive technologies from the frontmatter
        _techs = []
        if "tags" in fm and isinstance(fm["tags"], list):
            _techs = fm["tags"]
        elif "technologies" in fm and isinstance(fm["technologies"], list):
            _techs = fm["technologies"]

        if len(_techs) > 0:
            asset.technologies.clear()
            for tech_slug in _techs:
                technology = AssetTechnology.get_or_create(tech_slug)

                # if the technology is not multi lang
                if technology.lang is not None and technology.lang != "":
                    # skip technology because it does not match the asset lang
                    if technology.lang in ["us", "en"] and asset.lang not in ["us", "en"]:
                        continue
                    elif technology.lang != asset.lang:
                        continue

                asset.technologies.add(technology)

    return asset


def clean_asset_readme(asset: Asset):
    if asset.readme_raw is None or asset.readme_raw == "":
        return asset

    asset.last_cleaning_at = timezone.now()
    try:
        asset = clean_readme_relative_paths(asset)
        asset = clean_readme_hide_comments(asset)
        asset = clean_h1s(asset)
        asset = clean_content_variables(asset)
        readme = asset.get_readme(parse=True)
        if "html" in readme:
            asset.html = readme["html"]

        asset.cleaning_status = "OK"
        asset.save()
    except Exception as e:
        asset.cleaning_status = "ERROR"
        asset.cleaning_status_details = str(e)
        asset.save()

    return asset


def clean_content_variables(asset: Asset):
    logger.debug(f"Clearning content variables for readme for asset {asset.slug}")
    readme = asset.get_readme()
    pattern = (
        r"{%\s+([^\s%]+)\s+%}"  # This regex pattern matches {% variable_name %} or {% variable_name:"default_value" %}
    )
    markdown_text = readme["decoded"]
    logger.debug("Original text:" + markdown_text)

    variables_dict = {}
    variables = ContentVariable.objects.filter(academy=asset.academy).filter(Q(lang__isnull=True) | Q(lang=asset.lang))
    for varia in variables:
        if varia.value is None:
            variables_dict[varia.key] = varia.default_value
        else:
            variables_dict[varia.key] = varia.value

    logger.debug("Variables")
    logger.debug(variables_dict)

    def replace(match):
        variable_data = match.group(1).strip()
        variable_parts = variable_data.split(":", 1)  # Split variable name and default value

        variable_name = variable_parts[0].strip()
        logger.debug("Found variable " + variable_name)
        if len(variable_parts) > 1:
            default_value = variable_parts[1].strip()
        else:
            asset.log_error("missing-variable", f"Variable {variable_name} is missing and it has not default value")
            default_value = "{% " + variable_name + " %}"

        value = variables_dict.get(variable_name, default_value)
        return value if value is not None else match.group(0)

    replaced_text = re.sub(pattern, replace, markdown_text)
    logger.debug("Replaced text:" + replaced_text)
    asset.set_readme(replaced_text)
    return asset


def clean_readme_relative_paths(asset: Asset):
    readme = asset.get_readme()
    base_url = os.path.dirname(asset.readme_url)
    relative_urls = list(re.finditer(r'((?:\.\.?\/)+[^)"\']+)', readme["decoded"]))

    replaced = readme["decoded"]
    while len(relative_urls) > 0:
        match = relative_urls.pop(0)
        found_url = match.group()
        if found_url.endswith("\\"):
            found_url = found_url[:-1].strip()
        extension = pathlib.Path(found_url).suffix
        if (
            readme["decoded"][match.start() - 1] in ["(", "'", '"']
            and extension
            and extension.strip() in [".png", ".jpg", ".png", ".jpeg", ".svg", ".gif"]
        ):
            logger.debug("Replaced url: " + base_url + "/" + found_url + "?raw=true")
            replaced = replaced.replace(found_url, base_url + "/" + found_url + "?raw=true")

    asset.set_readme(replaced)
    return asset


def clean_readme_hide_comments(asset: Asset):
    logger.debug(f"Clearning readme for asset {asset.slug}")
    readme = asset.get_readme()
    regex = r"<!--\s*(:?end)?hide\s*-->"

    content = readme["decoded"]
    findings = list(re.finditer(regex, content))

    if len(findings) % 2 != 0:
        asset.log_error(AssetErrorLog.README_SYNTAX, "Readme with to many <!-- hide -> comments")
        raise Exception("Readme with to many <!-- hide -> comments")

    replaced = ""
    start_index = 0
    while len(findings) > 1:
        opening_comment = findings.pop(0)
        end_index = opening_comment.start()

        replaced += content[start_index:end_index]

        closing_comment = findings.pop(0)
        start_index = closing_comment.end()

    replaced += content[start_index:]
    asset.set_readme(replaced)
    return asset


def clean_h1s(asset: Asset):
    logger.debug(f"Clearning first heading 1 for {asset.slug}")
    readme = asset.get_readme()
    content = readme["decoded"].strip()

    frontmatter = ""
    frontmatter_regex = r"---\n(.*?\n)*?---\n"

    match = re.search(frontmatter_regex, content, flags=re.DOTALL)

    if match:

        frontmatter_content = match.group()
        frontmatter = frontmatter_content.strip() if frontmatter_content else ""

        content = content[match.end() :].strip()

    end = r".*\n"
    lines = list(re.finditer(end, content))
    if len(lines) == 0:
        logger.debug("no jump of lines found")
        return asset

    first_line_end = lines.pop(0).end()
    logger.debug("first line ends at")
    logger.debug(first_line_end)

    regex = r"\s?#\s[`\-_\w]+[`\-_\w\s]*\n"
    findings = list(re.finditer(regex, content[:first_line_end]))
    if len(findings) > 0:
        replaced = content[first_line_end:].strip()
        if frontmatter != "":
            replaced = f"{frontmatter}\n\n{replaced}"
        asset.set_readme(replaced)

    return asset


def screenshots_bucket():
    return os.getenv("SCREENSHOTS_BUCKET", "")


class AssetThumbnailGenerator:
    asset: Asset
    width: Optional[int]
    height: Optional[int]

    def __init__(self, asset: Asset, width: Optional[int] = 0, height: Optional[int] = 0) -> None:
        self.asset = asset
        self.width = width
        self.height = height

    def get_thumbnail_url(self) -> tuple[str, bool]:
        """
        Get thumbnail url for asset, the first element of tuple is the url, the second if is permanent
        redirect.
        """

        from breathecode.registry import tasks

        if not self.asset:
            return (self._get_default_url(), False)
        media = self._get_media()
        if not media:
            tasks.async_create_asset_thumbnail.delay(self.asset.slug)
            return (self._get_asset_url(), False)

        if not self._the_client_want_resize():
            # register click
            media.hits += 1
            media.save()

            if self.asset.preview is None or self.asset.preview == "":
                self.asset.preview = media.url
                self.asset.save()

            return (media.url, True)

        media_resolution = self._get_media_resolution(media.hash)
        if not media_resolution:
            # register click
            media.hits += 1
            media.save()
            tasks.async_resize_asset_thumbnail.delay(media.id, width=self.width, height=self.height)
            return (media.url, False)

        # register click
        media_resolution.hits += 1
        media_resolution.save()

        if self.asset.preview is None or self.asset.preview == "":
            self.asset.preview = media.url
            self.asset.save()

        return (f"{media.url}-{media_resolution.width}x{media_resolution.height}", True)

    def _get_default_url(self) -> str:
        return os.getenv("DEFAULT_ASSET_PREVIEW_URL", "")

    def _get_asset_url(self) -> str:
        return (self.asset and self.asset.preview) or self._get_default_url()

    def _get_media(self) -> Optional[Media]:
        if not self.asset:
            return None

        slug = self.asset.get_thumbnail_name().split(".")[0]
        return Media.objects.filter(slug=slug).first()

    def _get_media_resolution(self, hash: str) -> Optional[MediaResolution]:
        return MediaResolution.objects.filter(Q(width=self.width) | Q(height=self.height), hash=hash).first()

    def _the_client_want_resize(self) -> bool:
        """
        Check if the width of height value was provided, if both are provided return False
        """

        return bool((self.width and not self.height) or (not self.width and self.height))

    def create(self, delay=600):

        preview_url = self.asset.get_preview_generation_url()
        if preview_url is None:
            raise Exception("Not able to retrieve a preview generation url")

        filename = self.asset.get_thumbnail_name()
        url = set_query_parameter(preview_url, "slug", self.asset.slug)

        response = None
        try:
            logger.debug(f"Generating screenshot with URL {url}")
            query_string = urlencode(
                {
                    "key": os.environ.get("SCREENSHOT_MACHINE_KEY"),
                    "url": url,
                    "device": "desktop",
                    "delay": delay,
                    "cacheLimit": "0",
                    "dimension": "1024x707",
                }
            )
            response = requests.get(f"https://api.screenshotmachine.com?{query_string}", stream=True)

        except Exception as e:
            raise Exception("Error calling service to generate thumbnail screenshot: " + str(e))

        if response.status_code >= 400:
            raise Exception(
                "Unhandled error with async_create_asset_thumbnail, the cloud function `screenshots` "
                f"returns status code {response.status_code}"
            )

        storage = Storage()
        cloud_file = storage.file(screenshots_bucket(), filename)
        cloud_file.upload(response.content)

        self.asset.preview = cloud_file.url()
        self.asset.save()

        return self.asset


def process_asset_config(asset, config):

    if not config:
        raise Exception("No configuration json found")

    if asset.asset_type in ["QUIZ"]:
        raise Exception("Can only process exercise and project config objects")

    # only replace title and description of English language
    if "title" in config:
        if isinstance(config["title"], str):
            if asset.lang in ["", "us", "en"] or asset.title == "" or asset.title is None:
                asset.title = config["title"]
        elif isinstance(config["title"], dict) and asset.lang in config["title"]:
            asset.title = config["title"][asset.lang]

    if "description" in config:
        if isinstance(config["description"], str):
            # avoid replacing descriptions for other languages
            if asset.lang in ["", "us", "en"] or asset.description == "" or asset.description is None:
                asset.description = config["description"]
        # there are multiple translations, and the translation exists for this lang
        elif isinstance(config["description"], dict) and asset.lang in config["description"]:
            asset.description = config["description"][asset.lang]

    if "preview" in config:
        asset.preview = config["preview"]
    else:
        raise Exception("Missing preview URL")

    if "video-id" in config:
        asset.solution_video_url = get_video_url(str(config["video-id"]))
        asset.with_video = True

    if "video" in config and isinstance(config["video"], dict):
        if "intro" in config["video"] and config["video"]["intro"] is not None:
            if isinstance(config["video"]["intro"], str):
                asset.intro_video_url = get_video_url(str(config["video"]["intro"]))
            else:
                if "en" in config["video"]["intro"]:
                    config["video"]["intro"]["us"] = config["video"]["intro"]["en"]
                elif "us" in config["video"]["intro"]:
                    config["video"]["intro"]["en"] = config["video"]["intro"]["us"]

                if asset.lang in config["video"]["intro"]:
                    print("get_video_url", get_video_url(str(config["video"]["intro"][asset.lang])))
                    asset.intro_video_url = get_video_url(str(config["video"]["intro"][asset.lang]))

        if "solution" in config["video"] and config["video"]["solution"] is not None:
            if isinstance(config["video"]["solution"], str):
                asset.solution_video_url = get_video_url(str(config["video"]["solution"]))
                asset.with_video = True
                asset.with_solutions = True
            else:
                if "en" in config["video"]["solution"]:
                    config["video"]["solution"]["us"] = config["video"]["solution"]["en"]
                elif "us" in config["video"]["solution"]:
                    config["video"]["solution"]["en"] = config["video"]["solution"]["us"]

                if asset.lang in config["video"]["solution"]:
                    asset.with_solutions = True
                    asset.solution_video_url = get_video_url(str(config["video"]["solution"][asset.lang]))
                    asset.with_video = True

    if "duration" in config:
        asset.duration = config["duration"]

    if "template_url" in config:
        if asset.asset_type != "PROJECT":
            asset.log_error("template-url", "Only asset types projects can have templates")
        else:
            asset.template_url = config["template_url"]
    else:
        asset.template_url = None

    if "difficulty" in config:
        asset.difficulty = config["difficulty"].upper()
    if "videoSolutions" in config:
        asset.with_solutions = True
        asset.with_video = True

    if "agent" in config:
        asset.agent = config["agent"]

    if "solution" in config:
        asset.with_solutions = True
        if isinstance(config["solution"], str):
            asset.solution_url = config["solution"]
        elif isinstance(config["solution"], dict):
            if asset.lang in ["us", "en"]:
                if "us" in config["solution"]:
                    asset.solution_url = config["solution"]["us"]
                if "en" in config["solution"]:
                    asset.solution_url = config["solution"]["en"]
            elif asset.lang in config["solution"]:
                asset.solution_url = config["solution"][asset.lang]

    if "grading" not in config and ("projectType" not in config or config["projectType"] != "tutorial"):
        asset.interactive = False
        asset.gitpod = False
    elif "projectType" in config and config["projectType"] == "tutorial":
        asset.gitpod = "localhostOnly" not in config or not config["localhostOnly"]
        asset.interactive = True
    elif "grading" in config and config["grading"] in ["isolated", "incremental"]:
        asset.gitpod = "localhostOnly" not in config or not config["localhostOnly"]
        asset.interactive = True

    if "technologies" in config:
        asset.technologies.clear()
        for tech_slug in config["technologies"]:
            technology = AssetTechnology.get_or_create(tech_slug)
            # if the technology is not multi lang
            if technology.lang is not None and technology.lang != "":
                # skip technology because it does not match the asset lang
                if technology.lang in ["us", "en"] and asset.lang not in ["us", "en"]:
                    continue
                elif technology.lang != asset.lang:
                    continue
            asset.technologies.add(technology)

    if "delivery" in config:
        if "instructions" in config["delivery"]:
            if isinstance(config["delivery"]["instructions"], str):
                asset.delivery_instructions = config["delivery"]["instructions"]
            elif (
                isinstance(config["delivery"]["instructions"], dict)
                and asset.lang in config["delivery"]["instructions"]
            ):
                asset.delivery_instructions = config["delivery"]["instructions"][asset.lang]

        if "formats" in config["delivery"]:
            if isinstance(config["delivery"]["formats"], list):
                asset.delivery_formats = ",".join(config["delivery"]["formats"])
            elif isinstance(config["delivery"]["formats"], str):
                asset.delivery_formats = config["delivery"]["formats"]

        if "url" in asset.delivery_formats:
            if "regex" in config["delivery"] and isinstance(config["delivery"]["regex"], str):
                asset.delivery_regex_url = config["delivery"]["regex"].replace("\\\\", "\\")
    else:
        asset.delivery_instructions = ""
        asset.delivery_formats = "url"
        asset.delivery_regex_url = ""

    asset.save()
    return asset


def pull_learnpack_asset(github, asset: Asset, override_meta):

    if asset.readme_url is None:
        raise Exception("Missing Readme URL for asset " + asset.slug + ".")

    org_name, repo_name, branch_name = asset.get_repo_meta()
    repo = github.get_repo(f"{org_name}/{repo_name}")

    lang = asset.lang
    if lang is None or lang == "":
        raise Exception("Language for this asset is not defined, impossible to retrieve readme")
    elif lang in ["us", "en"]:
        lang = ""
    else:
        lang = "." + lang

    readme_file = None
    try:
        readme_file = repo.get_contents(f"README{lang}.md")
    except Exception:
        raise Exception(f"Translation on README{lang}.md not found")

    learn_file = None
    try:
        learn_file = repo.get_contents("learn.json")
    except Exception:
        try:
            learn_file = repo.get_contents(".learn/learn.json")
        except Exception:
            try:
                learn_file = repo.get_contents("bc.json")
            except Exception:
                try:
                    learn_file = repo.get_contents(".learn/bc.json")
                except Exception:
                    raise Exception("No configuration learn.json or bc.json file was found")

    base64_readme = str(readme_file.content)
    asset.readme_raw = base64_readme

    config = None
    if learn_file is not None and (asset.last_synch_at is None or override_meta):
        config = json.loads(learn_file.decoded_content.decode("utf-8"))
        asset.config = config

    asset = process_asset_config(asset, config)
    return asset


def pull_repo_dependencies(github, asset):
    """
    Pulls the main programming languages and their versions from a GitHub repository.

    Parameters:
    - github: Authenticated GitHub client instance (e.g., from PyGithub).
    - asset: Asset object with `get_repo_meta()` to retrieve repo metadata.
    - override_meta: Optional metadata to override repository details.

    Returns:
    - languages: Dictionary of main programming languages and their versions.
    """
    org_name, repo_name, branch_name = asset.get_repo_meta()

    # Access the repository
    repo = github.get_repo(f"{org_name}/{repo_name}")

    # Retrieve programming languages from GitHub
    languages = repo.get_languages()
    if not languages:
        return "No languages detected by Github"

    # Parse version from dependency files
    dependency_files = ["requirements.txt", "pyproject.toml", "Pipfile", "package.json"]
    language_versions = {}

    for file_name in dependency_files:
        try:
            content_file = repo.get_contents(file_name, ref=branch_name)
            content = content_file.decoded_content.decode("utf-8")
            detected_version = detect_language_version(file_name, content)
            if detected_version:
                language_versions.update(detected_version)
        except Exception:
            continue

    # Combine languages and versions
    combined = {lang: language_versions.get(lang, "unknown") for lang in languages}
    dependencies_str = ",".join(f"{lang.lower()}={version}" for lang, version in combined.items())
    return dependencies_str


def detect_language_version(file_name, content):
    import tomli

    """
    Detects the programming language version from a dependency file.

    Returns:
    - Dictionary of language and version detected.
    """
    if file_name == "requirements.txt":
        # Check for Python version in requirements.txt (e.g., python_version marker)
        if "python_version" in content:
            return {"Python": extract_python_version(content)}

    if file_name == "pyproject.toml":
        data = tomli.loads(content)
        version = data.get("tool", {}).get("poetry", {}).get("dependencies", {}).get("python", None)
        if version:
            return {"Python": version}

    if file_name == "package.json":
        import json

        data = json.loads(content)
        engines = data.get("engines", {})
        if "node" in engines:
            return {"Node.js": engines["node"]}

    if file_name == "Pipfile":

        data = tomli.loads(content)
        version = data.get("requires", {}).get("python_version", None)
        if version:
            return {"Python": version}

    return {}


def extract_python_version(content):
    """
    Extracts Python version from requirements.txt content.
    """
    for line in content.splitlines():
        if "python_version" in line:
            return line.split("python_version")[-1].strip(" ()=")
    return "unknown"


def pull_quiz_asset(github, asset: Asset):

    logger.debug(f"Sync pull_quiz_asset {asset.slug}")

    if asset.readme_url is None:
        raise Exception("Missing Readme URL for quiz " + asset.slug + ".")

    org_name, repo_name, branch_name = asset.get_repo_meta()
    repo = github.get_repo(f"{org_name}/{repo_name}")

    os.path.basename(asset.readme_url)

    if branch_name is None:
        raise Exception("Quiz URL must include branch name after blob")

    result = re.search(r"\/blob\/([\w\d_\-]+)\/(.+)", asset.readme_url)
    _, file_path = result.groups()
    logger.debug(f"Fetching quiz json: {file_path}")

    encoded_config = get_blob_content(repo, file_path, branch=branch_name).content
    decoded_config = Asset.decode(encoded_config)

    _config = json.loads(decoded_config)
    asset.config = _config

    # "slug":    "introduction-networking-es",
    # "name":    "Introducción a redes",
    # "difficulty":    "beginner",
    # "main":    "Bienvenido al mundo de las redes. Este primer paso te llevara a grandes cosas en el futuro...",
    # "results": "¡Felicidades! Ahora el mundo estará un poco más seguro gracias a tí...",
    # "technologies": ["redes"],
    # "badges": [
    #     { "slug": "cybersecurity_guru", "points": 5 }
    # ]
    if "info" in _config:
        _config = _config["info"]
        if "name" in _config and _config["name"] != "":
            asset.title = _config["name"]

        if "main" in _config and _config["main"]:
            asset.description = _config["main"]
        elif "description" in _config and _config["description"]:
            asset.description = _config["description"]

        if "technologies" in _config and _config["technologies"] != "":
            asset.technologies.clear()
            for tech_slug in _config["technologies"]:
                technology = AssetTechnology.get_or_create(tech_slug)
                asset.technologies.add(technology)

        if "difficulty" in _config and _config["technologies"] != "":
            asset.difficulty = _config["difficulty"]

    asset.save()

    if asset.assessment is None:
        asset = create_from_asset(asset)

    return asset


def test_asset(asset: Asset):
    try:

        validator = None
        if asset.asset_type == "LESSON":
            validator = LessonValidator(asset)
        elif asset.asset_type == "EXERCISE":
            validator = ExerciseValidator(asset)
        elif asset.asset_type == "PROJECT":
            validator = ProjectValidator(asset)
        elif asset.asset_type == "QUIZ":
            validator = QuizValidator(asset)
        elif asset.asset_type == "ARTICLE":
            validator = ArticleValidator(asset)

        validator.validate()
        asset.status_text = "Test Successfull"
        asset.test_status = "OK"
        asset.last_test_at = timezone.now()
        asset.save()
        return True
    except AssetException as e:
        asset.status_text = str(e)
        asset.test_status = e.severity
        asset.last_test_at = timezone.now()
        asset.save()
        raise e
        return False
    except Exception as e:
        asset.status_text = str(e)
        asset.test_status = "ERROR"
        asset.last_test_at = timezone.now()
        asset.save()
        raise e
        return False


def scan_asset_originality(asset: Asset):

    scan = OriginalityScan(asset=asset)
    try:
        credentials = asset.academy.credentialsoriginality
    except Exception as e:
        scan.status_text = "Error retriving originality credentials for academy: " + str(e)
        scan.status = "ERROR"
        scan.save()
        raise Exception(scan.status_text)

    try:

        readme = asset.get_readme(parse=True, remove_frontmatter=True)

        from bs4 import BeautifulSoup
        from markdown import markdown

        html = markdown(readme["html"])
        text = "".join(BeautifulSoup(html).findAll(text=True))

        scanner = OriginalityWrapper(credentials.token)
        result = scanner.detect(text)
        if isinstance(result, dict):
            scan.success = result["success"]
            scan.score_original = result["score"]["original"]
            scan.score_ai = result["score"]["ai"]
            scan.credits_used = result["credits_used"]
            scan.content = result["content"]
        else:
            raise Exception("Error receiving originality API response payload")

    except Exception as e:
        scan.status_text = "Error scanning originality for asset: " + str(e)
        scan.status = "ERROR"
        scan.save()
        raise Exception(scan.status_text)

    scan.status = "COMPLETED"
    scan.save()


def upload_image_to_bucket(img: AssetImage, asset=None):

    from ..services.google_cloud import Storage

    link = img.original_url
    if "github.com" in link and not "raw=true" in link:
        if "?" in link:
            link = link + "&raw=true"
        else:
            link = link + "?raw=true"

    r = requests.get(link, stream=True, timeout=2)
    if r.status_code != 200:
        raise Exception(f"Error downloading image from asset image {img.name}: {link}")

    found_mime = [mime for mime in allowed_mimes() if r.headers["content-type"] in mime]
    if len(found_mime) == 0:
        raise Exception(
            f"Skipping image download for {link} in asset image {img.name}, invalid mime {r.headers['content-type']}"
        )

    img.hash = hashlib.sha256(r.content).hexdigest()

    storage = Storage()

    extension = pathlib.Path(img.name).suffix
    cloud_file = storage.file(asset_images_bucket(), img.hash + extension)
    if not cloud_file.exists():
        cloud_file.upload(r.content)

    img.hash = img.hash
    img.mime = found_mime[0]
    img.bucket_url = cloud_file.url()
    img.download_status = "OK"
    img.save()

    if asset:
        img.assets.add(asset)

    return img


def add_syllabus_translations(_json: dict):
    if not isinstance(_json, dict) or "days" not in _json or not isinstance(_json["days"], list):
        return _json

    day_count = -1
    for day in _json.get("days", []):
        unique_technologies = {}
        day_count += 1
        for asset_type in ["assignments", "lessons", "quizzes", "replits"]:
            index = -1
            if asset_type not in day:
                continue
            for ass in day[asset_type]:
                index += 1
                slug = ass["slug"] if "slug" in ass else ass
                _asset = Asset.get_by_slug(slug)
                if _asset is not None:
                    if "slug" not in ass:
                        _json["days"][day_count][asset_type][index] = {
                            "slug": _asset.slug,
                            "title": _asset.title,
                        }
                    _json["days"][day_count][asset_type][index]["translations"] = {}
                    for a in _asset.all_translations.all():
                        _json["days"][day_count][asset_type][index]["translations"][a.lang] = {
                            "slug": a.slug,
                            "title": a.title,
                        }
                        # add translations technologies as well
                        _assetTechs = a.technologies.all()
                        for t in _assetTechs:
                            # Use the slug as a unique key to avoid duplicates
                            if t.slug not in unique_technologies:
                                unique_technologies[t.slug] = {"slug": t.slug, "title": t.title}

                    if _asset.lang not in _json["days"][day_count][asset_type][index]["translations"]:
                        _json["days"][day_count][asset_type][index]["translations"][_asset.lang] = {
                            "slug": _asset.slug,
                            "title": _asset.title,
                        }

                    _assetTechs = _asset.technologies.all()
                    for t in _assetTechs:
                        # Use the slug as a unique key to avoid duplicates
                        if t.slug not in unique_technologies:
                            unique_technologies[t.slug] = {"slug": t.slug, "title": t.title}

                    _json["days"][day_count]["technologies"] = list(unique_technologies.values())
    return _json
