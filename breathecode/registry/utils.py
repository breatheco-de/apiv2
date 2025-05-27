import asyncio
import logging
import re
import aiohttp
import requests
from bs4 import BeautifulSoup

from breathecode.authenticate.models import CredentialsGithub
from breathecode.services.github import Github, GithubAuthException

logger = logging.getLogger(__name__)


class AssetErrorLogType:
    SLUG_NOT_FOUND = "slug-not-found"
    DIFFERENT_TYPE = "different-type"
    EMPTY_README = "empty-readme"
    EMPTY_CATEGORY = "empty-category"
    INVALID_OWNER = "invalid-owner"
    MISSING_TECHNOLOGIES = "missing-technologies"
    POOR_DESCRIPTION = "poor-description"
    EMPTY_HTML = "empty-html"
    INVALID_URL = "invalid-url"
    INVALID_LANGUAGE = "invalid-language"
    INVALID_README_URL = "invalid-readme-url"
    INVALID_IMAGE = "invalid-image"
    README_SYNTAX = "readme-syntax-error"


def is_url(value):
    url_pattern = re.compile(
        r"^(https?://)?"  # optional http or https scheme
        r"(([A-Za-z0-9-]+\.)+[A-Za-z]{2,})"  # domain name
        r"(:\d+)?"  # optional port
        r"(\/[-A-Za-z0-9@:%._\+~#=]*)*"  # path
        r"(\?[;&A-Za-z0-9%_.~+=-]*)?"  # query string
        r"(#[-A-Za-z0-9_]*)?$"  # fragment locator
    )
    return re.match(url_pattern, value) is not None


def get_urls_from_html(html_content):
    soup = BeautifulSoup(html_content, features="lxml")
    urls = []

    anchors = soup.findAll("a")
    for a in anchors:
        urls.append(a.get("href"))

    images = images = soup.findAll("img")
    for img in images:
        urls.append(img.get("src"))

    return urls


def _shared_test_url(url, allow_relative=False, allow_hash=True):
    if url is None or url == "":
        raise Exception("Empty url")

    if not allow_hash and url.startswith("#"):
        raise Exception("Not allowed hash url: " + url)

    # Fix: Check for relative but exclude protocol-relative
    is_relative = url.startswith("../") or url.startswith("./") or (url.startswith("/") and not url.startswith("//"))
    is_hash = url.startswith("#")  # Keep this check separate

    if not allow_relative and is_relative:
        raise Exception("Not allowed relative url: " + url)

    # Return flags to indicate if it needs network check
    return is_relative, is_hash


def test_url(url, allow_relative=False, allow_hash=True):
    is_relative, is_hash = _shared_test_url(url, allow_relative, allow_hash)

    # Handle URL validation for HTTP/HTTPS URLs
    # Only attempt network request if it's not relative and not just a hash
    if not is_relative and not is_hash:
        if not re.match(r"^[a-zA-Z]+://", url) and not url.startswith("//"):
            raise Exception(f"Invalid URL format (Missing Schema?): {url}")

        try:
            response = requests.head(url, allow_redirects=False, timeout=25)
            if response.status_code not in [200, 302, 301, 307]:
                raise Exception(f"Invalid URL with code {response.status_code}: {url}")

        except requests.exceptions.Timeout:
            raise Exception(f"Timeout connecting to URL: {url}")

        except requests.exceptions.ConnectionError:
            raise Exception(f"Connection error for URL: {url}")

        except requests.exceptions.RequestException as e:
            raise Exception(f"Error connecting to URL: {url} - {str(e)}")


async def atest_url(url, allow_relative=False, allow_hash=True):
    is_relative, is_hash = _shared_test_url(url, allow_relative, allow_hash)

    # Handle URL validation for HTTP/HTTPS URLs
    # Only attempt network request if it's not relative and not just a hash
    if not is_relative and not is_hash:
        if not re.match(r"^[a-zA-Z]+://", url) and not url.startswith("//"):
            raise Exception(f"Invalid URL format (Missing Schema?): {url}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(
                    url, allow_redirects=False, timeout=aiohttp.ClientTimeout(total=25)
                ) as response:
                    if response.status not in [200, 302, 301, 307]:
                        raise Exception(f"Invalid URL with code {response.status}: {url}")

        except asyncio.TimeoutError:
            raise Exception(f"Timeout connecting to URL: {url}")

        except aiohttp.ClientConnectorError:
            raise Exception(f"Connection error for URL: {url}")

        except aiohttp.ClientError as e:
            raise Exception(f"Error connecting to URL: {url} - {str(e)}")


class AssetException(Exception):

    def __init__(self, message="", severity="ERROR"):
        all_severities = ["ERROR", "WARNING"]
        if severity in all_severities:
            self.severity = severity
        else:
            raise Exception("Invalid AssetException severity " + severity)


class AssetValidator:
    base_warns = ["translations", "technologies"]
    base_errors = ["lang", "urls", "category", "preview", "images", "readme_url", "description"]
    warns = []
    errors = []

    def __init__(self, _asset, log_errors=False):
        from breathecode.registry.models import Asset

        self.asset: Asset = _asset
        self.log_errors = log_errors
        self.warns = self.base_warns + self.warns
        self.errors = self.base_errors + self.errors

    def error(self, type, _msg):
        if self.log_errors:
            self.asset.log_error(type, _msg)
        raise Exception(_msg)

    def validate(self):

        try:
            for validation in self.errors:
                if hasattr(self, validation):
                    getattr(self, validation)()
                else:
                    raise Exception("Invalid asset error validation " + validation)
        except Exception as e:
            raise AssetException(str(e), severity="ERROR")

        try:
            for validation in self.warns:
                if hasattr(self, validation):
                    getattr(self, validation)()
                else:
                    raise Exception("Invalid asset warning validation " + validation)
        except Exception as e:
            raise AssetException(str(e), severity="WARNING")

    def readme_url(self):
        if self.asset.readme_url is not None or self.asset.readme_url != "":
            if not self.asset.owner:
                self.error(
                    AssetErrorLogType.INVALID_OWNER,
                    "Asset must have an owner and the owner must have write access to the readme file",
                )

            credentials = CredentialsGithub.objects.filter(user=self.asset.owner).first()
            if credentials is None:
                self.error(AssetErrorLogType.INVALID_OWNER, "Github credentials for asset owner were not found")

            gb = Github(credentials.token)
            try:
                if not gb.file_exists(self.asset.readme_url):
                    self.error(AssetErrorLogType.INVALID_README_URL, "Readme URL points to a missing file")
            except GithubAuthException:
                self.error(
                    AssetErrorLogType.INVALID_OWNER,
                    "Cannot connect to github to validate readme url, please fix owner or credentials",
                )
            except Exception as e:
                raise AssetException(str(e), severity="ERROR")

    def urls(self):

        readme = self.asset.get_readme(parse=True)
        if "html" in readme:
            urls = get_urls_from_html(readme["html"])
            for url in urls:
                test_url(url, allow_relative=False)

    def lang(self):

        if self.asset.lang is None or self.asset.lang == "":
            self.error(
                AssetErrorLogType.INVALID_LANGUAGE, "Asset is missing a language or has an invalid language assigned"
            )

    def translations(self):
        if self.asset.all_translations.exists() == 0:
            raise Exception("No translations")

    def technologies(self):
        if self.asset.technologies.count() < 2:
            self.error(AssetErrorLogType.MISSING_TECHNOLOGIES, "Asset should have at least 2 technology tags")

    def difficulty(self):
        if not self.asset.difficulty:
            raise Exception("No difficulty")

    def description(self):
        if not self.asset.description or len(self.asset.description) < 100:
            self.error(AssetErrorLogType.POOR_DESCRIPTION, "Description is too small or empty")

    def preview(self):
        pass
        # TODO: Comment this out for now, we will uncomment when preview url generates automatically
        # if self.asset.preview is None:
        #     raise Exception('Missing preview url')
        # else:
        #     test_url(self.asset.preview, allow_relative=False, allow_hash=False)

    def readme(self):
        if self.asset.readme is None or self.asset.readme == "" and not self.asset.external:
            self.error(AssetErrorLogType.EMPTY_README, "Asset is missing a readme file")

    def category(self):
        if self.asset.category is None:
            self.error(AssetErrorLogType.EMPTY_CATEGORY, "Asset is missing a category")

    def images(self):
        images = self.asset.images.all()
        for image in images:
            if image.download_status != "OK":
                self.error(
                    AssetErrorLogType.INVALID_IMAGE,
                    "Check the asset images, there seems to be images not properly downloaded",
                )


class LessonValidator(AssetValidator):
    warns = []
    errors = ["readme"]


class ArticleValidator(AssetValidator):
    warns = []
    errors = ["readme"]


class StarterValidator(AssetValidator):
    warns = []
    errors = ["readme"]


class ExerciseValidator(AssetValidator):
    warns = ["difficulty"]
    errors = ["readme", "preview"]


class ProjectValidator(ExerciseValidator):
    warns = ["difficulty"]
    errors = ["readme", "preview"]


class QuizValidator(AssetValidator):
    warns = ["difficulty"]
    errors = ["preview"]


class OriginalityWrapper:

    def __init__(self, token):
        self.token = token

    def detect(self, text):

        return self._request("scan/ai", method="POST", body={"content": text})

    def _request(self, url, method="GET", body=None):

        headers = {"X-OAI-API-KEY": self.token}
        response = requests.request(
            method=method, url="https://api.originality.ai/api/v1/" + url, data=body, headers=headers, timeout=2
        )

        if response.status_code == 200:
            result = response.json()
            # {
            #     "success": true,
            #     "score": {
            #         "original": 0.8502796292304993,
            #         "ai": 0.14972037076950073
            #     },
            #     "credits_used": 1,
            #     "content": "A delicious cup of tea is a simple and timeless pleasure, and for many people it's even more than that..."
            # }
            return result
        else:
            msg = f"Error {response.status_code} while request originality API"
            logger.error(msg)
            raise Exception(msg)


def prompt_technologies(technologies):
    lines = []
    for tech in technologies:
        if not tech.is_deprecated and tech.visibility in ["PUBLIC", "UNLISTED"] and tech.parent is None:
            lines.append(f"Technology title: {tech.title}")
            lines.append(f"Slug: {tech.slug}")
            lines.append(f"Description: {tech.description}")
            if tech.lang:
                lines.append(f"Language: {tech.lang}")
            else:
                lines.append("Language: english and spanish")
            lines.append(f"Priority: {tech.sort_priority}")
            lines.append("")  # Add a blank line between technologies
            lines.append("---------------------")  # Add a blank line between technologies
            lines.append("")  # Add a blank line between technologies
    return "\n".join(lines)
