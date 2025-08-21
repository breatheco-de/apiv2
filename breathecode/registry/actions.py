import base64
import hashlib
import json
import logging
import os
import pathlib
import re
from typing import Optional
from urllib.parse import urlencode

import aiohttp
import requests
from asgiref.sync import sync_to_async
from django.db.models import Q
from django.template.loader import get_template
from django.utils import timezone
from github import Github

from breathecode.assessment.actions import create_from_asset
from breathecode.authenticate.models import CredentialsGithub
from breathecode.media.models import Media, MediaResolution
from breathecode.services.google_cloud.storage import Storage
from breathecode.utils.views import set_query_parameter

from .models import ASSET_STATUS, Asset, AssetImage, AssetTechnology, ContentVariable, OriginalityScan
from .serializers import AssetBigSerializer
from .utils import (
    ArticleValidator,
    AssetErrorLogType,
    AssetException,
    ExerciseValidator,
    LessonValidator,
    OriginalityWrapper,
    ProjectValidator,
    QuizValidator,
    StarterValidator,
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


@sync_to_async
def apull_from_github(asset_slug, author_id=None, override_meta=False):
    return pull_from_github(asset_slug, author_id, override_meta)


def push_to_github(asset_slug, owner=None):

    logger.debug(f"Push asset {asset_slug} to github")

    asset = None
    try:

        asset = Asset.objects.filter(slug=asset_slug).first()
        if asset is None:
            raise Exception(f"Asset with slug {asset_slug} not found when attempting github push")

        asset.status_text = "Starting to push..."
        asset.sync_status = "PENDING"
        asset.save()

        if owner is None:
            if asset.owner is not None:
                owner = asset.owner
            elif asset.author is not None:
                owner = asset.author

        if asset.external:
            raise Exception('Asset is marked as "external" so it cannot push to github')

        if owner is None:
            raise Exception("Asset must have an owner with write permissions on the repository")

        if asset.readme_url is None or "github.com" not in asset.readme_url:
            raise Exception(f"Missing or invalid URL on {asset_slug}, it does not belong to github.com")

        credentials = CredentialsGithub.objects.filter(user__id=owner.id).first()
        if credentials is None:
            raise Exception(
                f"Github credentials for user {owner.first_name} {owner.last_name} (id: {owner.id}) not found when synching asset {asset_slug}"
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


@sync_to_async
def apush_to_github(asset_slug, owner=None):
    return push_to_github(asset_slug, owner)


def get_blob_content(repo, path_name, branch="main"):
    """
    Get blob content from a GitHub repository with enhanced error handling for private repositories.

    Args:
        repo: GitHub repository object
        path_name: Path to the file in the repository
        branch: Branch name (default: "main")

    Returns:
        Blob object or None if not found

    Raises:
        Exception: For authentication, permission, or other access issues
    """
    if "?" in path_name:
        path_name = path_name.split("?")[0]

    try:
        # First get the branch reference
        ref = repo.get_git_ref(f"heads/{branch}")

        # Then get the tree
        tree = repo.get_git_tree(ref.object.sha, recursive="/" in path_name).tree

        # Look for path in tree
        sha = [x.sha for x in tree if x.path == path_name]
        if not sha:
            # File not found in tree
            logger.debug(f"File '{path_name}' not found in repository tree on branch '{branch}'")
            return None

        # We have sha, get the blob
        blob = repo.get_git_blob(sha[0])
        logger.debug(f"Successfully retrieved blob for '{path_name}' from branch '{branch}'")
        return blob

    except Exception as e:
        error_str = str(e).lower()

        # Handle specific error types
        if "404" in error_str or "not found" in error_str:
            if f"heads/{branch}" in str(e) or f"branch {branch}" in str(e):
                raise Exception(f"Branch '{branch}' not found in repository")
            else:
                logger.debug(f"File '{path_name}' not found in repository on branch '{branch}'")
                return None
        elif "403" in error_str or "forbidden" in error_str:
            raise Exception(
                f"Access forbidden when retrieving '{path_name}' from branch '{branch}'. Repository is accessible but file/branch permissions may be restricted."
            )
        elif "401" in error_str or "unauthorized" in error_str:
            raise Exception(
                f"Authentication failed when retrieving '{path_name}' from branch '{branch}'. Check GitHub credentials."
            )
        else:
            raise Exception(f"Error retrieving '{path_name}' from branch '{branch}': {str(e)}")


def set_blob_content(repo, path_name, content, file_name, branch="main", create_or_update=False, is_binary=False):
    """
    Upload content (text or binary) to GitHub repository.

    Args:
        repo: GitHub repository object
        path_name: Path where to store the file
        content: Content to upload (string for text, bytes for binary)
        file_name: Name of the file for commit message
        branch: Branch to upload to
        create_or_update: Whether to create file if it doesn't exist
        is_binary: Whether the content is binary (images, etc.) or text

    Returns:
        GitHub API response or None if file not found and create_or_update=False
    """
    if is_binary:
        if content is None or len(content) == 0:
            raise Exception(f"Binary content is empty for {path_name}")
    else:
        if content is None or content == "":
            raise Exception(f"Blob content is empty for {path_name}")

    # first get the branch reference
    ref = repo.get_git_ref(f"heads/{branch}")
    # then get the tree
    tree = repo.get_git_tree(ref.object.sha, recursive="/" in path_name).tree
    # look for path in tree
    file = [x for x in tree if x.path == path_name]
    if not file:
        # file not found
        if create_or_update:
            # create new file - PyGithub handles base64 encoding automatically for binary content
            return repo.create_file(path_name, f"Create {file_name}", content, branch=branch)
        else:
            # well, not found and not allowed to create
            return None

    # update existing file - PyGithub handles base64 encoding automatically for binary content
    return repo.update_file(file[0].path, f"Update {file_name}", content, file[0].sha, branch=branch)


def get_screenshot_machine_params(url: str, dimension: str = "1200x630", **kwargs):
    screenshot_key = os.getenv("SCREENSHOT_MACHINE_KEY", "")
    params = {
        "key": screenshot_key,
        "url": url,
        "dimension": dimension,
        "device": "desktop",
        "delay": kwargs.get("delay", "1000"),
        "cacheLimit": "0",
        **kwargs,
    }

    # Remove these parameters from kwargs since they're now in params
    if "device" in kwargs:
        del kwargs["device"]
    if "delay" in kwargs:
        del kwargs["delay"]
    if "cacheLimit" in kwargs:
        del kwargs["cacheLimit"]

    return params


def generate_screenshot(url: str, dimension: str = "1200x630", **kwargs):
    params = get_screenshot_machine_params(url, dimension, **kwargs)

    # Always use stream=True for screenshot downloads to handle large files properly
    return requests.get(f"https://api.screenshotmachine.com?{urlencode(params)}", timeout=25, stream=True)


async def agenerate_screenshot(url: str, dimension: str = "1200x630", **kwargs):
    """
    Asynchronous version of generate_screenshot using aiohttp instead of requests.
    This should only be used in async views, not in Celery tasks.
    """

    params = get_screenshot_machine_params(url, dimension, **kwargs)

    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.screenshotmachine.com/", params=params, timeout=25) as response:
            if response.status != 200:
                logger.error(f"Screenshot service returned error code: {response.status}")
                return response

            content = await response.read()

            response.content = content
            response.status_code = response.status
            return response


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

    # First check if we have access to the repository itself
    # This is especially important for private repositories
    try:
        repo = github.get_repo(f"{org_name}/{repo_name}")

        # Log repository accessibility for debugging
        try:
            repo_info = repo.raw_data
            is_private = repo_info.get("private", False)
            asset.allow_contributions = not is_private
            logger.debug(
                f"Repository {org_name}/{repo_name} is accessible for lesson sync. "
                f"Private: {is_private}, Allow contributions: {asset.allow_contributions}"
            )
        except Exception:
            logger.warning(f"Could not get repository details for lesson sync {org_name}/{repo_name}")
            asset.allow_contributions = True

    except Exception as e:
        error_str = str(e).lower()
        if "404" in error_str or "not found" in error_str:
            raise Exception(f"Repository {org_name}/{repo_name} not found or not accessible")
        elif "403" in error_str or "forbidden" in error_str:
            raise Exception(
                f"Access forbidden to repository {org_name}/{repo_name}. Check GitHub credentials and repository permissions."
            )
        elif "401" in error_str or "unauthorized" in error_str:
            raise Exception(
                f"GitHub authentication failed for repository {org_name}/{repo_name}. Check GitHub credentials."
            )
        else:
            raise Exception(f"Error accessing repository {org_name}/{repo_name}: {str(e)}")

    os.path.basename(asset.readme_url)

    if branch_name is None:
        raise Exception("Lesson URL must include branch name after blob")

    result = re.search(r"\/blob\/([\w\d_\-]+)\/(.+)", asset.readme_url)
    _, file_path = result.groups()
    logger.debug(f"Fetching readme: {file_path}")

    # Try to get the readme file with enhanced error handling
    try:
        blob_file = get_blob_content(repo, file_path, branch=branch_name)
        if blob_file is None:
            raise Exception(
                f"Lesson README file '{file_path}' not found in repository {org_name}/{repo_name} on branch '{branch_name}'"
            )

        base64_readme = blob_file.content
        asset.readme_raw = base64_readme

        # this avoids to keep using the old readme file, we do have a new version
        # the asset.get_readme function will not update the asset if we keep the old version
        if asset.readme_raw is not None:
            asset.readme = asset.readme_raw

        logger.debug(f"Successfully retrieved lesson README from {org_name}/{repo_name}")

    except Exception as e:
        # get_blob_content already handles most error categorization, so we can re-raise
        # but add more context for lesson-specific errors
        error_str = str(e).lower()
        if "nothing was found" in error_str or "not found" in error_str:
            raise Exception(
                f"Lesson README file '{file_path}' not found in repository {org_name}/{repo_name} on branch '{branch_name}'"
            )
        else:
            raise Exception(f"Error retrieving lesson README from repository {org_name}/{repo_name}: {str(e)}")

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


def clean_asset_readme(asset: Asset, silent=True):
    """
    Clean the asset readme, if silent is True, it will not raise an exception if the readme is not found
    """
    if asset.readme_raw is None or asset.readme_raw == "":
        return asset

    asset.last_cleaning_at = timezone.now()
    try:
        asset = clean_readme_relative_paths(asset)
        asset = clean_readme_hide_comments(asset)
        asset = replace_private_github_urls(asset)
        asset = clean_h1s(asset)
        asset = clean_content_variables(asset)

        readme = asset.get_readme(parse=True, silent=silent)
        if "html" in readme:
            asset.html = readme["html"]

        asset.cleaning_status = "OK"
        asset.save()
    except Exception as e:
        asset.cleaning_status = "ERROR"
        asset.cleaning_status_details = str(e)
        asset.save()

    return asset


@sync_to_async
def aclean_asset_readme(asset: Asset, silent=True):
    return clean_asset_readme(asset)


def clean_content_variables(asset: Asset):
    logger.debug(f"Clearning content variables for readme for asset {asset.slug}")
    readme = asset.get_readme()
    pattern = (
        r"{%\s+([^\s%]+)\s+%}"  # This regex pattern matches {% variable_name %} or {% variable_name:"default_value" %}
    )
    markdown_text = readme["decoded"]

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
    # logger.debug("Replaced text:" + replaced_text)
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


def replace_private_github_urls(asset: Asset):
    """
    Replace internal GitHub URLs with internal link proxy URLs.

    This function scans the asset's readme content for GitHub URLs that point to the same
    repository as the asset's readme_url. When found, it replaces them with internal
    proxy URLs that use the asset owner's GitHub credentials to access private content.

    Args:
        asset: The Asset object to process

    Returns:
        Asset: The updated asset with replaced URLs
    """
    from breathecode.registry.utils import is_internal_github_url
    from breathecode.services.github import Github

    if not asset.readme_url or not asset.owner:
        return asset

    readme = asset.get_readme()
    content = readme["decoded"]

    # Find all GitHub URLs in the content
    github_url_pattern = r'https://github\.com/[^\s\)"\'\]]+|https://raw\.githubusercontent\.com/[^\s\)"\'\]]+'
    github_urls = re.findall(github_url_pattern, content)

    if not github_urls:
        return asset

    # Parse the asset's repository information
    github_service = Github()
    asset_repo_info = github_service.parse_github_url(asset.readme_url)

    if not asset_repo_info:
        return asset

    replaced_content = content

    for url in github_urls:
        # Check if this URL points to the same repository
        if is_internal_github_url(url, asset.readme_url):
            url_info = github_service.parse_github_url(url)

            # Only replace URLs that point to files (blob, raw)
            if url_info and url_info["url_type"] in ["blob", "raw"] and url_info.get("path"):
                # Create the internal link URL
                # Token can be added as a query parameter when accessing the link
                internal_url = f"{os.getenv('API_URL')}/asset/internal-link?id={asset.id}&path={url_info['path']}"
                replaced_content = replaced_content.replace(url, internal_url)

    if replaced_content != content:
        asset.set_readme(replaced_content)

    return asset


def clean_readme_hide_comments(asset: Asset):
    logger.debug(f"Clearning readme for asset {asset.slug}")
    readme = asset.get_readme()
    regex = r"<!--\s*(:?end)?hide\s*-->"

    content = readme["decoded"]
    findings = list(re.finditer(regex, content))

    if len(findings) % 2 != 0:
        asset.log_error(AssetErrorLogType.README_SYNTAX, "Readme with to many <!-- hide -> comments")
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

    regex = r"^\s?#\s[`\-_\w¿¡?!]+[`\-_\w\s¿¡?!]*\n"
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

    @sync_to_async
    def aget_thumbnail_url(self):
        return self.get_thumbnail_url()

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

    def create(self, delay=25000, **kwargs):
        """
        Create a thumbnail image for an asset. This method runs synchronously.
        """

        preview_url = self.asset.get_preview_generation_url()
        if preview_url is None:
            raise Exception("Not able to retrieve a preview generation url")

        filename = self.asset.get_thumbnail_name()
        url = set_query_parameter(preview_url, "slug", self.asset.slug)

        response = None
        try:
            logger.debug(f"Generating screenshot with URL {url}")
            response = generate_screenshot(url, "1024x707", delay=delay)

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

    async def acreate(self, delay=25000):
        """
        Asynchronous version of the create method for use in async views.
        """

        preview_url = self.asset.get_preview_generation_url()
        if preview_url is None:
            raise Exception("Not able to retrieve a preview generation url")

        filename = self.asset.get_thumbnail_name()
        url = set_query_parameter(preview_url, "slug", self.asset.slug)

        response = None
        try:
            logger.debug(f"Generating screenshot with URL {url}")
            response = await agenerate_screenshot(url, "1024x707", delay=delay)

        except Exception as e:
            raise Exception("Error calling service to generate thumbnail screenshot: " + str(e))

        if response.status_code >= 400:
            raise Exception(
                "Unhandled error with async_create_asset_thumbnail, the cloud function `screenshots` "
                f"returns status code {response.status_code}"
            )

        storage = Storage()
        cloud_file = storage.file(screenshots_bucket(), filename)
        await cloud_file.aupload(response.content)

        self.asset.preview = cloud_file.url()
        await self.asset.asave()

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

    if "editor" in config:
        if "agent" in config["editor"]:
            asset.agent = config["editor"]["agent"]

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

    if "gitpod" in config:
        if config["gitpod"] in ["True", "true", "1", True]:
            asset.gitpod = True
        elif config["gitpod"] in ["False", "false", "0", False]:
            asset.gitpod = False

    asset.save()
    return asset


def pull_learnpack_asset(github, asset: Asset, override_meta):

    if asset.readme_url is None:
        raise Exception("Missing Readme URL for asset " + asset.slug + ".")

    org_name, repo_name, branch_name = asset.get_repo_meta()

    # First check if we have access to the repository itself
    # This is especially important for private repositories
    try:
        repo = github.get_repo(f"{org_name}/{repo_name}")

        # Log repository accessibility for debugging
        try:
            repo_info = repo.raw_data
            is_private = repo_info.get("private", False)
            asset.allow_contributions = not is_private
            logger.debug(
                f"Repository {org_name}/{repo_name} is accessible for learnpack asset sync. "
                f"Private: {is_private}, Allow contributions: {asset.allow_contributions}"
            )
        except Exception:
            logger.warning(f"Could not get repository details for learnpack asset sync {org_name}/{repo_name}")
            asset.allow_contributions = True

    except Exception as e:
        error_str = str(e).lower()
        # Add more detailed debugging information
        logger.error(f"GitHub API Error accessing {org_name}/{repo_name}: {str(e)}")
        logger.error(f"Full exception details: {repr(e)}")

        if "404" in error_str or "not found" in error_str:
            raise Exception(
                f"Repository {org_name}/{repo_name} not found or not accessible. This could be due to: 1) Repository doesn't exist, 2) Repository is private and token lacks 'repo' scope, 3) User doesn't have access to the repository"
            )
        elif "403" in error_str or "forbidden" in error_str:
            raise Exception(
                f"Access forbidden to repository {org_name}/{repo_name}. Check GitHub credentials and repository permissions."
            )
        elif "401" in error_str or "unauthorized" in error_str:
            raise Exception(
                f"GitHub authentication failed for repository {org_name}/{repo_name}. Check GitHub credentials."
            )
        else:
            raise Exception(f"Error accessing repository {org_name}/{repo_name}: {str(e)}")

    lang = asset.lang
    if lang is None or lang == "":
        raise Exception("Language for this asset is not defined, impossible to retrieve readme")
    elif lang in ["us", "en"]:
        lang = ""
    else:
        lang = "." + lang

    # Try to get README file with better error handling
    readme_file = None
    readme_filename = f"README{lang}.md"
    try:
        readme_file = repo.get_contents(readme_filename)
        logger.debug(f"Successfully retrieved {readme_filename} from {org_name}/{repo_name}")
    except Exception as e:
        error_str = str(e).lower()
        if "404" in error_str or "not found" in error_str:
            raise Exception(f"README file '{readme_filename}' not found in repository {org_name}/{repo_name}")
        elif "403" in error_str or "forbidden" in error_str:
            logger.warning(
                f"Access forbidden for {readme_filename} in repository {org_name}/{repo_name}. "
                f"Repository is accessible but file permissions may be restricted."
            )
            raise Exception(f"Access forbidden to README file '{readme_filename}' in repository {org_name}/{repo_name}")
        elif "401" in error_str or "unauthorized" in error_str:
            raise Exception(
                f"Authentication failed when accessing README file '{readme_filename}' in repository {org_name}/{repo_name}"
            )
        else:
            raise Exception(
                f"Error retrieving README file '{readme_filename}' from repository {org_name}/{repo_name}: {str(e)}"
            )

    # Try to get configuration file with better error handling
    learn_file = None
    config_files = ["learn.json", ".learn/learn.json", "bc.json", ".learn/bc.json"]

    for config_filename in config_files:
        try:
            learn_file = repo.get_contents(config_filename)
            logger.debug(f"Successfully retrieved config file {config_filename} from {org_name}/{repo_name}")
            break
        except Exception as e:
            error_str = str(e).lower()

            # For config files, only log detailed errors for the last attempt
            if config_filename == config_files[-1]:
                if "404" in error_str or "not found" in error_str:
                    logger.debug(
                        f"No configuration files found in repository {org_name}/{repo_name}. Tried: {', '.join(config_files)}"
                    )
                elif "403" in error_str or "forbidden" in error_str:
                    logger.warning(
                        f"Access forbidden to configuration files in repository {org_name}/{repo_name}. "
                        f"Repository is accessible but file permissions may be restricted."
                    )
                elif "401" in error_str or "unauthorized" in error_str:
                    logger.warning(
                        f"Authentication failed when accessing configuration files in repository {org_name}/{repo_name}"
                    )
                else:
                    logger.warning(
                        f"Error accessing configuration files in repository {org_name}/{repo_name}: {str(e)}"
                    )
            else:
                # For intermediate attempts, just log debug info
                logger.debug(f"Config file {config_filename} not found, trying next option")
                continue

    # If no config file was found, raise an exception
    if learn_file is None:
        raise Exception(
            f"No configuration file (learn.json, bc.json) found in repository {org_name}/{repo_name}. Tried: {', '.join(config_files)}"
        )

    base64_readme = str(readme_file.content)
    asset.readme_raw = base64_readme

    config = None
    if learn_file is not None and (asset.last_synch_at is None or override_meta):
        try:
            config = json.loads(learn_file.decoded_content.decode("utf-8"))
            asset.config = config
            logger.debug(f"Successfully parsed configuration from {org_name}/{repo_name}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON in configuration file: {str(e)}")
        except Exception as e:
            raise Exception(f"Error processing configuration file: {str(e)}")

    asset = process_asset_config(asset, config)

    if asset.asset_type == "PROJECT" and asset.solution_url:
        from breathecode.services.github import Github as GithubService

        github_service = GithubService()
        solution_url_info = github_service.parse_github_url(asset.solution_url)
        solution_path = solution_url_info.get("path")
        solution_branch = solution_url_info.get("branch")
        solution_owner = solution_url_info.get("owner")
        solution_repo = solution_url_info.get("repo")

        if solution_path and solution_branch:
            try:
                solution_repo = github.get_repo(f"{solution_owner}/{solution_repo}")
                solution_blob = get_blob_content(solution_repo, solution_path, branch=solution_branch)
                if solution_blob is not None:
                    raw_content = base64.b64decode(solution_blob.content).decode("utf-8")
                    asset.solution_readme = process_solution_content(raw_content)
                    logger.debug(
                        f"Successfully retrieved solution README from {asset.solution_url} for asset {asset.slug}"
                    )
                else:
                    error_msg = f"Solution file '{solution_path}' not found in repository on branch '{solution_branch}'"
                    logger.error(f"{error_msg} for asset {asset.slug}")
                    raise Exception(error_msg)
            except Exception as e:
                error_str = str(e).lower()
                if "404" in error_str or "not found" in error_str:
                    error_msg = f"Solution repository {solution_repo} not found or not accessible"
                elif "403" in error_str or "forbidden" in error_str:
                    error_msg = f"Access forbidden to solution repository {solution_repo}. Check GitHub credentials and repository permissions."
                elif "401" in error_str or "unauthorized" in error_str:
                    error_msg = f"GitHub authentication failed for solution repository {solution_repo}. Check GitHub credentials."
                else:
                    error_msg = f"Error accessing solution README file at {asset.solution_url}: {str(e)}"

                logger.error(f"{error_msg} for asset {asset.slug}")
                raise Exception(error_msg)
        else:
            try:
                response = requests.get(asset.solution_url)
                if response.status_code == 200:
                    asset.solution_readme = process_solution_content(
                        response.text, response.headers.get("content-type")
                    )
                    logger.debug(
                        f"Successfully retrieved solution README via direct GET from {asset.solution_url} for asset {asset.slug}"
                    )
                else:
                    error_msg = f"Failed to retrieve solution README via direct GET from {asset.solution_url}, status code: {response.status_code}"
                    logger.error(f"{error_msg} for asset {asset.slug}")
                    raise Exception(error_msg)
            except Exception as e:
                error_msg = f"Error making direct GET request to {asset.solution_url}: {str(e)}"
                logger.error(f"{error_msg} for asset {asset.slug}")
                raise Exception(error_msg)

    return asset


def pull_repo_dependencies(github, asset):
    """
    Pulls the main programming languages and their versions from a GitHub repository.

    Parameters:
    - github: Authenticated GitHub client instance (e.g., from PyGithub).
    - asset: Asset object with `get_repo_meta()` to retrieve repo metadata.

    Returns:
    - languages: Dictionary of main programming languages and their versions.
    """
    org_name, repo_name, branch_name = asset.get_repo_meta()

    # First check if we have access to the repository itself
    # This is especially important for private repositories
    try:
        repo = github.get_repo(f"{org_name}/{repo_name}")

        # Log repository accessibility for debugging
        try:
            repo_info = repo.raw_data
            logger.debug(
                f"Repository {org_name}/{repo_name} is accessible for dependency analysis. "
                f"Private: {repo_info.get('private', 'unknown')}"
            )
        except Exception:
            logger.warning(f"Could not get repository details for dependency analysis {org_name}/{repo_name}")

    except Exception as e:
        error_str = str(e).lower()
        if "404" in error_str or "not found" in error_str:
            raise Exception(f"Repository {org_name}/{repo_name} not found or not accessible for dependency analysis")
        elif "403" in error_str or "forbidden" in error_str:
            raise Exception(
                f"Access forbidden to repository {org_name}/{repo_name} for dependency analysis. Check GitHub credentials and repository permissions."
            )
        elif "401" in error_str or "unauthorized" in error_str:
            raise Exception(
                f"GitHub authentication failed for repository {org_name}/{repo_name} dependency analysis. Check GitHub credentials."
            )
        else:
            raise Exception(f"Error accessing repository {org_name}/{repo_name} for dependency analysis: {str(e)}")

    # Retrieve programming languages from GitHub
    try:
        languages = repo.get_languages()
        if not languages:
            logger.debug(f"No programming languages detected by GitHub for repository {org_name}/{repo_name}")
            return ""  # Return empty string for no languages detected
    except Exception as e:
        logger.warning(f"Error retrieving programming languages from repository {org_name}/{repo_name}: {str(e)}")
        raise Exception(f"Error retrieving programming languages from repository {org_name}/{repo_name}: {str(e)}")

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
                logger.debug(f"Found version info in {file_name}: {detected_version}")
        except Exception as e:
            error_str = str(e).lower()

            # Only log detailed errors for meaningful issues, not normal 404s
            if "404" in error_str or "not found" in error_str:
                logger.debug(f"Dependency file {file_name} not found in repository {org_name}/{repo_name}")
            elif "403" in error_str or "forbidden" in error_str:
                logger.warning(
                    f"Access forbidden to dependency file {file_name} in repository {org_name}/{repo_name}. "
                    f"Repository is accessible but file permissions may be restricted."
                )
            elif "401" in error_str or "unauthorized" in error_str:
                logger.warning(
                    f"Authentication failed when accessing dependency file {file_name} in repository {org_name}/{repo_name}"
                )
            else:
                logger.debug(
                    f"Error accessing dependency file {file_name} in repository {org_name}/{repo_name}: {str(e)}"
                )
            continue

    # Combine languages and versions
    combined = {lang: language_versions.get(lang, "unknown") for lang in languages}
    dependencies_str = ",".join(f"{lang.lower()}={version}" for lang, version in combined.items())

    logger.debug(f"Dependencies analysis complete for {org_name}/{repo_name}: {dependencies_str}")
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
            return {"python": extract_python_version(content)}

    if file_name == "pyproject.toml":
        data = tomli.loads(content)
        version = data.get("tool", {}).get("poetry", {}).get("dependencies", {}).get("python", None)
        if version:
            return {"python": version}

    if file_name == "package.json":
        import json

        data = json.loads(content)
        engines = data.get("engines", {})
        if "node" in engines:
            return {"javascript": engines["node"]}

    if file_name == "Pipfile":

        data = tomli.loads(content)
        version = data.get("requires", {}).get("python_version", None)
        if version:
            return {"python": version}

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

    # First check if we have access to the repository itself
    # This is especially important for private repositories
    try:
        repo = github.get_repo(f"{org_name}/{repo_name}")

        # Log repository accessibility for debugging
        try:
            repo_info = repo.raw_data
            is_private = repo_info.get("private", False)
            asset.allow_contributions = not is_private
            logger.debug(
                f"Repository {org_name}/{repo_name} is accessible for quiz asset sync. "
                f"Private: {is_private}, Allow contributions: {asset.allow_contributions}"
            )
        except Exception:
            logger.warning(f"Could not get repository details for quiz asset sync {org_name}/{repo_name}")
            asset.allow_contributions = True

    except Exception as e:
        error_str = str(e).lower()
        if "404" in error_str or "not found" in error_str:
            raise Exception(f"Repository {org_name}/{repo_name} not found or not accessible")
        elif "403" in error_str or "forbidden" in error_str:
            raise Exception(
                f"Access forbidden to repository {org_name}/{repo_name}. Check GitHub credentials and repository permissions."
            )
        elif "401" in error_str or "unauthorized" in error_str:
            raise Exception(
                f"GitHub authentication failed for repository {org_name}/{repo_name}. Check GitHub credentials. {str(error_str)}"
            )
        else:
            raise Exception(f"Error accessing repository {org_name}/{repo_name}: {str(e)}")

    os.path.basename(asset.readme_url)

    if branch_name is None:
        raise Exception("Quiz URL must include branch name after blob")

    result = re.search(r"\/blob\/([\w\d_\-]+)\/(.+)", asset.readme_url)
    _, file_path = result.groups()
    logger.debug(f"Fetching quiz json: {file_path}")

    # Try to get the quiz configuration file with better error handling
    try:
        blob_file = get_blob_content(repo, file_path, branch=branch_name)
        if blob_file is None:
            raise Exception(f"Quiz configuration file '{file_path}' not found in repository {org_name}/{repo_name}")

        encoded_config = blob_file.content
        decoded_config = Asset.decode(encoded_config)

        try:
            _config = json.loads(decoded_config)
            asset.config = _config
            logger.debug(f"Successfully parsed quiz configuration from {org_name}/{repo_name}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON in quiz configuration file '{file_path}': {str(e)}")

    except Exception as e:
        # Check if this is a repository access error vs file-specific error
        error_str = str(e).lower()
        if "404" in error_str or "not found" in error_str:
            raise Exception(f"Quiz configuration file '{file_path}' not found in repository {org_name}/{repo_name}")
        elif "403" in error_str or "forbidden" in error_str:
            raise Exception(
                f"Access forbidden to quiz configuration file '{file_path}' in repository {org_name}/{repo_name}"
            )
        elif "401" in error_str or "unauthorized" in error_str:
            raise Exception(
                f"Authentication failed when accessing quiz configuration file '{file_path}' in repository {org_name}/{repo_name}"
            )
        else:
            raise Exception(
                f"Error retrieving quiz configuration from '{file_path}' in repository {org_name}/{repo_name}: {str(e)}"
            )

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


def test_asset(asset: Asset, log_errors=False, reset_errors=False):
    """
    This function is used to test an asset.
    log_errors: If True, it will log the errors in the AssetErrorLog model.
    reset_errors: If True, it will erase all previous errors about this asset.
    """
    try:

        validator = None
        if asset.asset_type == "LESSON":
            validator = LessonValidator(asset, log_errors, reset_errors)
        if asset.asset_type == "STARTER":
            validator = StarterValidator(asset, log_errors, reset_errors)
        elif asset.asset_type == "EXERCISE":
            validator = ExerciseValidator(asset, log_errors, reset_errors)
        elif asset.asset_type == "PROJECT":
            validator = ProjectValidator(asset, log_errors, reset_errors)
        elif asset.asset_type == "QUIZ":
            validator = QuizValidator(asset, log_errors, reset_errors)
        elif asset.asset_type == "ARTICLE":
            validator = ArticleValidator(asset, log_errors, reset_errors)

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
    except Exception as e:
        asset.status_text = str(e)
        asset.test_status = "ERROR"
        asset.last_test_at = timezone.now()
        asset.save()
        raise e


@sync_to_async
def atest_asset(asset: Asset, log_errors=False, reset_errors=False):
    return test_asset(asset, log_errors, reset_errors)


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


@sync_to_async
def ascan_asset_originality(asset: Asset):
    return scan_asset_originality(asset)


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
                        asset_techs = a.technologies.all()
                        for t in asset_techs:
                            # Use the slug as a unique key to avoid duplicates
                            if t.slug not in unique_technologies:
                                unique_technologies[t.slug] = {"slug": t.slug, "title": t.title}

                    if _asset.lang not in _json["days"][day_count][asset_type][index]["translations"]:
                        _json["days"][day_count][asset_type][index]["translations"][_asset.lang] = {
                            "slug": _asset.slug,
                            "title": _asset.title,
                        }

                    asset_techs = _asset.technologies.all()
                    for t in asset_techs:
                        # Use the slug as a unique key to avoid duplicates
                        if t.slug not in unique_technologies:
                            unique_technologies[t.slug] = {"slug": t.slug, "title": t.title}

                    _json["days"][day_count]["technologies"] = list(unique_technologies.values())
    return _json


def push_project_or_exercise_to_github(asset_slug, create_or_update=False, organization_github_username=None):
    """
    Push a project or exercise asset to GitHub.

    This function uploads the asset.config content as learn.json and all translation
    READMEs to their respective locations in the GitHub repository.

    The function automatically detects whether to create a new repository or update an existing one:
    - If asset has readme_url or url pointing to GitHub -> UPDATE mode (regardless of create_or_update)
    - If asset has no GitHub URLs and create_or_update=True -> CREATE mode
    - If asset has no GitHub URLs and create_or_update=False -> ERROR (cannot update non-existent repo)

    GitHub credentials are resolved in the following order:
    1. asset.owner (if exists)
    2. asset.author (if exists)
    3. asset.academy.github_owner (if exists and asset has no owner/author)

    Args:
        asset_slug (str): The slug of the asset to push
        create_or_update (bool): If True, allows creating repository when no GitHub URLs exist.
                                If False, only allows updating existing repositories.
        organization_github_username (str, optional): GitHub organization username for repo creation

    Returns:
        Asset: The updated asset object

    Raises:
        Exception: For various error conditions with translated messages
    """
    from capyc.core.i18n import translation
    from breathecode.authenticate.models import AcademyAuthSettings
    from breathecode.services.github import Github as GithubService

    logger.debug(f"Push project/exercise {asset_slug} to github")

    asset = None
    try:
        asset = Asset.objects.filter(slug=asset_slug).first()
        if asset is None:
            raise Exception(f"Asset with slug {asset_slug} not found when attempting to push to github")

        # Validate asset type
        if asset.asset_type not in ["PROJECT", "EXERCISE"]:
            raise Exception(
                translation(
                    en=f"Asset type {asset.asset_type} is not supported. Only PROJECT and EXERCISE assets can be pushed to GitHub.",
                    es=f"El tipo de asset {asset.asset_type} no está soportado. Solo assets de tipo PROJECT y EXERCISE se pueden subir a GitHub.",
                )
            )

        asset.status_text = "Starting to push to GitHub..."
        asset.sync_status = "PENDING"
        asset.save()

        # Determine operation mode based on existing URLs
        has_existing_repo = bool(asset.readme_url and "github.com" in asset.readme_url) or bool(
            asset.url and "github.com" in asset.url
        )

        if has_existing_repo:
            # Repository exists, we're in update mode
            operation_mode = "update"
            logger.debug(f"Asset {asset_slug} has existing repository, using update mode")

            # Ensure we have a valid readme_url for updates
            if not asset.readme_url or "github.com" not in asset.readme_url:
                raise Exception(
                    translation(
                        en=f"Missing or invalid readme_url on {asset_slug}, it must point to github.com for updates",
                        es=f"readme_url faltante o inválida en {asset_slug}, debe apuntar a github.com para actualizaciones",
                    )
                )

            # Set asset.url based on readme_url if empty
            if not asset.url and asset.readme_url:
                # Extract organization and repo name from readme_url
                import re

                result = re.search(r"https?:\/\/github\.com\/([\w\-]+)\/([\w\-]+)\/?", asset.readme_url)
                if result:
                    org_name = result.group(1)
                    repo_name = result.group(2)
                    asset.url = f"https://github.com/{org_name}/{repo_name}"
                    asset.save()
        else:
            # No existing repository
            if create_or_update:
                # We're allowed to create a new repository
                operation_mode = "create"
                logger.debug(f"Asset {asset_slug} has no existing repository, using create mode")
            else:
                # We're not allowed to create, only update
                raise Exception(
                    translation(
                        en=f"Asset {asset_slug} has no existing repository URLs (readme_url/url) and create_or_update=False. Cannot proceed with update-only mode.",
                        es=f"El asset {asset_slug} no tiene URLs de repositorio existentes (readme_url/url) y create_or_update=False. No se puede proceder en modo solo actualización.",
                    )
                )

        # Get owner credentials
        owner = asset.owner

        # If no owner/author, try to use academy's github_owner
        if owner is None and asset.academy:
            auth_settings = AcademyAuthSettings.objects.filter(academy=asset.academy).first()
            if auth_settings and auth_settings.github_owner:
                owner = auth_settings.github_owner
                asset.owner = owner
                asset.save()
                logger.debug(f"Using academy's github_owner {owner.id} for asset {asset_slug}")

        if owner is None:
            raise Exception(
                translation(
                    en="Asset must have an owner, author, or academy with GitHub credentials",
                    es="El asset debe tener un propietario, autor, o academia con credenciales de GitHub",
                )
            )

        credentials = CredentialsGithub.objects.filter(user__id=owner.id).first()
        if credentials is None:
            raise Exception(
                translation(
                    en=f"GitHub credentials not found for user {owner.first_name} {owner.last_name} (id: {owner.id})",
                    es=f"Credenciales de GitHub no encontradas para el usuario {owner.first_name} {owner.last_name} (id: {owner.id})",
                )
            )

        # Initialize GitHub service
        github_service = GithubService(token=credentials.token)
        github = Github(credentials.token)

        # Handle repository creation or access based on operation mode
        if operation_mode == "create":
            # Get organization username
            org_username = organization_github_username
            if not org_username and asset.academy:
                auth_settings = AcademyAuthSettings.objects.filter(academy=asset.academy).first()
                if auth_settings and auth_settings.github_username:
                    org_username = auth_settings.github_username

            if not org_username:
                raise Exception(
                    translation(
                        en="Organization GitHub username is required for repository creation",
                        es="Se requiere el nombre de usuario de GitHub de la organización para crear el repositorio",
                    )
                )

            # Create repository
            logger.debug(f"Creating repository {org_username}/{asset.slug}")
            repo_data = github_service.create_repository(
                owner=org_username,
                repo_name=asset.slug,
                description=asset.description or f"{asset.asset_type}: {asset.title}",
                private=True,
            )
            logger.debug(f"Repository created successfully: {repo_data.get('html_url', 'Unknown URL')}")

            # Set asset URLs based on created repository
            repo_url = f"https://github.com/{org_username}/{asset.slug}"
            asset.url = repo_url
            asset.readme_url = f"{repo_url}/blob/main/README.md"
            asset.save()

            # Give GitHub a moment to fully initialize the repository
            import time

            time.sleep(2)

            # Get the repo object for further operations
            repo = github.get_repo(f"{org_username}/{asset.slug}")
            logger.debug(f"Retrieved repository object: {repo.full_name}")
        else:
            # Update mode: use existing repository
            org_name, repo_name, branch_name = asset.get_repo_meta()
            repo = github.get_repo(f"{org_name}/{repo_name}")
            logger.debug(f"Using existing repository {org_name}/{repo_name}")

        # Upload preview image first (if exists)
        if asset.preview and asset.config:
            logger.debug(f"Uploading preview image for asset {asset.slug}")
            try:
                # Try to download the preview image directly first
                preview_response = requests.get(asset.preview, stream=True, timeout=30)
                image_content = None
                image_base64 = None

                if preview_response.status_code == 200:
                    image_content = preview_response.content
                    image_base64 = base64.b64encode(image_content).decode("utf-8")
                    logger.debug(f"Successfully downloaded preview image directly from {asset.preview}")
                else:
                    logger.debug(
                        f"Direct download failed (status {preview_response.status_code}), trying GitHub API fallback"
                    )

                    # Fallback: Try to download using GitHub API if it's a GitHub URL
                    if "github.com" in asset.preview:
                        try:
                            from breathecode.services.github import Github as GithubService

                            github_service = GithubService(token=credentials.token)
                            url_info = github_service.parse_github_url(asset.preview)

                            if url_info and url_info.get("path"):
                                # Get the file from GitHub API
                                github_repo = github.get_repo(f"{url_info['owner']}/{url_info['repo']}")
                                blob_file = get_blob_content(
                                    github_repo, url_info["path"], branch=url_info.get("branch", "main")
                                )

                                if blob_file:
                                    # blob_file.content is already base64 encoded from GitHub API
                                    image_base64 = blob_file.content
                                    image_content = base64.b64decode(image_base64)
                                    logger.debug(
                                        f"Successfully downloaded preview image via GitHub API from {asset.preview}"
                                    )
                                else:
                                    logger.warning(f"Could not find preview image file via GitHub API: {asset.preview}")
                            else:
                                logger.warning(f"Could not parse GitHub URL for preview image: {asset.preview}")

                        except Exception as api_error:
                            logger.warning(f"GitHub API fallback failed for preview image: {str(api_error)}")

                if image_content and image_base64:
                    # Determine image filename and extension
                    import pathlib
                    from urllib.parse import urlparse

                    parsed_url = urlparse(asset.preview)
                    path = parsed_url.path

                    # Try to get extension from URL path
                    extension = pathlib.Path(path).suffix
                    if not extension:
                        # Try to get extension from content-type header if available
                        content_type = ""
                        if preview_response.status_code == 200:
                            content_type = preview_response.headers.get("content-type", "")

                        if "png" in content_type:
                            extension = ".png"
                        elif "jpg" in content_type or "jpeg" in content_type:
                            extension = ".jpg"
                        elif "gif" in content_type:
                            extension = ".gif"
                        elif "svg" in content_type:
                            extension = ".svg"
                        else:
                            extension = ".png"  # Default

                    preview_filename = f"preview{extension}"

                    # Upload image to repository
                    try:
                        result = set_blob_content(
                            repo,
                            preview_filename,
                            image_content,
                            preview_filename,
                            create_or_update=True,
                            is_binary=True,
                        )

                        if result and "commit" in result:
                            # Update asset.config with new preview URL
                            new_preview_url = f"{asset.url}/blob/main/{preview_filename}?raw=true"
                            asset.config["preview"] = new_preview_url
                            asset.preview = new_preview_url
                            asset.save()
                            logger.debug(
                                f"Successfully uploaded preview image and updated config with URL: {new_preview_url}"
                            )
                        else:
                            logger.warning(f"Preview image upload may have failed for {preview_filename}")

                    except Exception as e:
                        logger.warning(f"Failed to upload preview image {preview_filename}: {str(e)}")
                        # Don't fail the entire process, just continue without updating preview
                else:
                    logger.warning(
                        f"Could not download preview image from {asset.preview} using direct download or GitHub API fallback"
                    )

            except Exception as e:
                logger.warning(f"Error processing preview image for asset {asset.slug}: {str(e)}")
                # Don't fail the entire process, just continue

        # Upload learn.json (asset.config)
        if asset.config:
            logger.debug(f"Uploading learn.json for asset {asset.slug}")
            config_content = json.dumps(asset.config, indent=4)

            # Determine config file location
            config_files = ["learn.json", ".learn/learn.json", "bc.json", ".learn/bc.json"]
            config_path = "learn.json"  # Default

            # Try to find existing config file location
            for config_file in config_files:
                try:
                    existing_file = get_blob_content(repo, config_file)
                    if existing_file is not None:
                        config_path = config_file
                        logger.debug(f"Found existing config at {config_file}")
                        break
                except Exception:
                    continue

            # Upload or update config file
            try:
                logger.debug(f"Attempting to upload/update {config_path} in {repo.full_name}")
                result = set_blob_content(repo, config_path, config_content, "learn.json", create_or_update=True)
                if result and "commit" in result:
                    asset.github_commit_hash = result["commit"].sha
                    logger.debug(f"Successfully uploaded/updated {config_path}")
            except Exception as e:
                logger.error(f"Error in config file upload process for {config_path} in {repo.full_name}: {str(e)}")
                # Handle any other GitHub API errors
                raise Exception(f"Error uploading {config_path}: {str(e)}")

        # Get all translations including the main asset
        translations = list(asset.all_translations.all())
        if asset not in translations:
            translations.append(asset)

        # Upload README files for each translation
        for translation_asset in translations:
            if not translation_asset.readme_raw:
                logger.debug(f"Skipping {translation_asset.slug} - no readme_raw content")
                continue

            logger.debug(f"Uploading README for translation {translation_asset.slug}")

            # Determine README filename based on language
            lang = translation_asset.lang
            if lang in ["us", "en", "", None]:
                readme_filename = "README.md"
            else:
                readme_filename = f"README.{lang}.md"

            # Decode the readme content
            readme_content = base64.b64decode(translation_asset.readme_raw.encode("utf-8")).decode("utf-8")

            # Upload or update README file
            try:
                logger.debug(f"Attempting to upload/update {readme_filename} in {repo.full_name}")
                result = set_blob_content(repo, readme_filename, readme_content, readme_filename, create_or_update=True)
                if result and "commit" in result:
                    if translation_asset == asset:
                        asset.github_commit_hash = result["commit"].sha
                    logger.debug(f"Successfully uploaded/updated {readme_filename}")
            except Exception as e:
                logger.error(f"Error in README file upload process for {readme_filename} in {repo.full_name}: {str(e)}")
                # Handle any other GitHub API errors
                raise Exception(f"Error uploading {readme_filename}: {str(e)}")

        asset.status_text = "Successfully pushed to GitHub"
        asset.sync_status = "OK"
        asset.last_synch_at = timezone.now()
        asset.save()
        logger.debug(f"Successfully pushed asset {asset_slug} to GitHub")

        return asset

    except Exception as e:
        logger.exception(e)
        message = str(e).replace('"', "'")

        logger.error(f"Error pushing {asset_slug} to GitHub: " + message)

        if asset is not None:
            asset.status_text = message
            asset.sync_status = "ERROR"
            asset.save()

        raise e


@sync_to_async
def apush_project_or_exercise_to_github(asset_slug, create_or_update=False, organization_github_username=None):
    return push_project_or_exercise_to_github(asset_slug, create_or_update, organization_github_username)


def convert_jupyter_notebook_to_markdown(notebook_content: str) -> str:
    """
    Convert Jupyter notebook content to markdown format.

    Args:
        notebook_content: The raw content of the Jupyter notebook (JSON string)

    Returns:
        str: The converted markdown content

    Raises:
        Exception: If the notebook content is invalid or conversion fails
    """
    try:
        import nbformat
        from nbconvert import MarkdownExporter

        notebook = nbformat.reads(notebook_content, as_version=4)

        markdown_exporter = MarkdownExporter()

        markdown_content, _ = markdown_exporter.from_notebook_node(notebook)

        return markdown_content

    except Exception as e:
        logger.error(f"Error converting Jupyter notebook to markdown: {str(e)}")
        raise Exception(f"Failed to convert Jupyter notebook to markdown: {str(e)}")


def is_jupyter_notebook(content: str) -> bool:
    """
    Check if the given content is a Jupyter notebook.

    Args:
        content: The content to check

    Returns:
        bool: True if the content appears to be a Jupyter notebook
    """
    try:
        import json

        data = json.loads(content)

        return isinstance(data, dict) and "cells" in data and "metadata" in data and "nbformat" in data
    except (json.JSONDecodeError, TypeError):
        return False


def process_solution_content(content: str, content_type: str = None) -> str:
    """
    Process solution content, converting Jupyter notebooks to markdown if needed.

    This function automatically detects Jupyter notebook content (either by content-type
    header or by analyzing the JSON structure) and converts it to markdown format using
    nbconvert. This ensures that solution content is always in a readable markdown format
    regardless of whether it was originally a Jupyter notebook or markdown file.

    Args:
        content: The raw solution content
        content_type: Optional content type hint (e.g., 'application/x-ipynb+json' for notebooks)

    Returns:
        str: The processed content (markdown if converted from notebook, original otherwise)

    Example:
        # Jupyter notebook content will be converted to markdown
        notebook_json = '{"cells": [{"cell_type": "markdown", "source": ["# Test"]}]}'
        result = process_solution_content(notebook_json)  # Auto-detection by content
        # result will be "# Test" (markdown format)

        # Regular markdown content will be left unchanged
        markdown_content = "# Test\nThis is markdown."
        result = process_solution_content(markdown_content)
        # result will be "# Test\nThis is markdown." (unchanged)
    """
    if not content:
        return content

    is_notebook = content_type == "application/x-ipynb+json" or is_jupyter_notebook(content)

    if is_notebook:
        logger.debug("Detected Jupyter notebook in solution content, converting to markdown")
        return convert_jupyter_notebook_to_markdown(content)

    return content
