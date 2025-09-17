"""
Registry utility functions for asset validation.

This module includes a trusted URL system that allows skipping validation for specific domains
and URLs that are known to be reliable but may have intermittent connectivity issues.

The trusted URL system supports:
- Trusted domains: Any URL from these domains will be skipped
- Trusted URLs: Specific URLs (ignoring query strings) that will be skipped

Configuration is done through TRUSTED_DOMAINS and TRUSTED_URLS sets below.
"""

import asyncio
import logging
import re
import aiohttp
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse

from breathecode.authenticate.models import CredentialsGithub
from breathecode.services.github import Github, GithubAuthException

logger = logging.getLogger(__name__)

# Trusted domains and URLs configuration
TRUSTED_DOMAINS = {
    'exploit-db.com',
    # Add more trusted domains here as needed
    # Common domains that might have reliability issues but are trusted:
    'twitter.com',
    'x.com',
    'example.com',
    'whatsmyname.app',
    'namechk.com'
    # 'stackoverflow.com',
}

TRUSTED_URLS = {
    # Add trusted full URLs here (without query strings)
    # 'https://example.com/specific/path',
    # 'https://another-site.com/another/path',
}


def normalize_url_for_comparison(url):
    """
    Normalize a URL by removing query strings and fragments for comparison.
    Returns the normalized URL or None if the URL is invalid.
    """
    try:
        parsed = urlparse(url)
        # Remove query and fragment
        normalized = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
        return normalized
    except Exception:
        return None


def is_trusted_url(url):
    """
    Check if a URL is in the trusted domains or trusted URLs lists.
    Returns True if the URL should be trusted and skipped from validation.
    """
    if not url:
        return False
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Remove 'www.' prefix for domain comparison
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Check if domain is in trusted domains
        if domain in TRUSTED_DOMAINS:
            return True
        
        # Check if the normalized URL (without query string) is in trusted URLs
        normalized_url = normalize_url_for_comparison(url)
        if normalized_url and normalized_url in TRUSTED_URLS:
            return True
        
        return False
    except Exception:
        return False

def get_trusted_domains():
    """
    Get a copy of the current trusted domains set.
    """
    return TRUSTED_DOMAINS.copy()


def get_trusted_urls():
    """
    Get a copy of the current trusted URLs set.
    """
    return TRUSTED_URLS.copy()


class AssetErrorLogType:
    SLUG_NOT_FOUND = "slug-not-found"
    DIFFERENT_TYPE = "different-type"
    EMPTY_README = "empty-readme"
    EMPTY_CATEGORY = "empty-category"
    INVALID_OWNER = "invalid-owner"
    MISSING_TECHNOLOGIES = "missing-technologies"
    MISSING_DIFFICULTY = "missing-difficulty"
    MISSING_TRANSLATIONS = "missing-translations"
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
    
def extract_urls_from_text(text):
    """
    Extract valid http/https URLs from any text.
    """
    url_pattern = re.compile(r'https?://[^\s\'"<>]+')
    return url_pattern.findall(text or "")


def get_urls_from_html(html_content):
    soup = BeautifulSoup(html_content, features="lxml")
    urls = []

    # Anchor tags
    for a in soup.find_all("a"):
        href = a.get("href")
        if href:
            urls.append(href)

    # Image tags
    for img in soup.find_all("img"):
        src = img.get("src")
        if src and "data:" not in src:
            urls.append(src)

    # Extract URLs from <code>, <pre>, and full page text
    text_blocks = soup.find_all(["code", "pre"])
    text_blocks.append(soup)  # add full document text

    for el in text_blocks:
        text = el.get_text()
        if text:
            urls += extract_urls_from_text(text)

    # Deduplicate and clean
    return list(set(filter(None, urls)))


def is_internal_github_url(url, asset_readme_url):
    """
    Check if a URL points to the same GitHub repository as the asset's readme_url.
    Internal URLs are those that point to blobs, files, or paths within the same repository.
    Uses the Github service's parse_github_url method to avoid code duplication.
    """
    if not url or not asset_readme_url:
        return False

    # Use Github service to parse URLs (we don't need authentication for parsing)
    github_service = Github()

    # Parse both URLs
    url_parsed = github_service.parse_github_url(url)
    readme_parsed = github_service.parse_github_url(asset_readme_url)

    # If either URL is not a GitHub URL, it's not internal
    if not (url_parsed and readme_parsed):
        return False

    # Check if both URLs point to the same repository
    return url_parsed["owner"] == readme_parsed["owner"] and url_parsed["repo"] == readme_parsed["repo"]


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
        # Check if URL is trusted and should be skipped
        if is_trusted_url(url):
            print(f"✅ Skipping validation for trusted URL: {url}")
            return

        if not re.match(r"^[a-zA-Z]+://", url) and not url.startswith("//"):
            raise Exception(f"Invalid URL format (Missing Schema?): {url}")

        try:
            # Try HEAD request first
            response = requests.head(url, allow_redirects=True, timeout=25)
            print(f"🔍 Validating external URL: {url} with status code {response.status_code}")

            # If HEAD request fails with 405 (Method Not Allowed) or 404, try GET as fallback
            if response.status_code in [405, 404]:
                print(f"🔄 HEAD request failed with {response.status_code}, trying GET request as fallback")
                response = requests.get(url, allow_redirects=True, timeout=25)
                print(f"🔍 GET fallback for {url} returned status code {response.status_code}")

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
        # Check if URL is trusted and should be skipped
        if is_trusted_url(url):
            print(f"✅ Skipping validation for trusted URL: {url}")
            return

        if not re.match(r"^[a-zA-Z]+://", url) and not url.startswith("//"):
            raise Exception(f"Invalid URL format (Missing Schema?): {url}")

        try:
            async with aiohttp.ClientSession() as session:
                # Try HEAD request first
                async with session.head(
                    url, allow_redirects=False, timeout=aiohttp.ClientTimeout(total=25)
                ) as response:
                    # If HEAD request fails with 405 (Method Not Allowed) or 404, try GET as fallback
                    if response.status in [405, 404]:
                        print(f"🔄 HEAD request failed with {response.status}, trying GET request as fallback")
                        async with session.get(
                            url, allow_redirects=False, timeout=aiohttp.ClientTimeout(total=25)
                        ) as get_response:
                            print(f"🔍 GET fallback for {url} returned status code {get_response.status}")
                            if get_response.status not in [200, 302, 301, 307]:
                                raise Exception(f"Invalid URL with code {get_response.status}: {url}")
                    elif response.status not in [200, 302, 301, 307]:
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

    def __init__(self, _asset, log_errors=False, reset_errors=False):
        from breathecode.registry.models import Asset

        self.asset: Asset = _asset
        self.log_errors = log_errors
        self.reset_errors = reset_errors
        self.warns = self.base_warns + self.warns
        self.errors = self.base_errors + self.errors

    def _reset_asset_errors(self):
        """
        Reset all existing AssetErrorLog entries for this asset.
        This prevents duplicate errors when running validation multiple times.
        """
        if not self.reset_errors:
            return

        from breathecode.registry.models import AssetErrorLog

        # Get all error types that could be generated during validation
        all_error_types = []
        for error_type in dir(AssetErrorLogType):
            if not error_type.startswith("_"):  # Skip private attributes
                all_error_types.append(getattr(AssetErrorLogType, error_type))

        # Delete existing error logs for this asset of validation error types
        deleted_count = AssetErrorLog.objects.filter(asset=self.asset, slug__in=all_error_types).delete()[0]

        if deleted_count > 0:
            logger.debug(f"Reset {deleted_count} previous error logs for asset {self.asset.slug}")

    def error(self, type, _msg):
        if self.log_errors:
            self.asset.log_error(type, _msg)
        raise Exception(_msg)

    def warning(self, type, _msg):
        pass

    def validate(self):
        # Reset errors before starting validation if requested
        self._reset_asset_errors()

        try:
            for validation in self.errors:
                if hasattr(self, validation):
                    print(f"🔍 Validating errors for: {validation}")
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
        if self.asset.readme_url is not None and self.asset.readme_url != "":
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
                # First, let's get repository information for debugging
                parsed_url = gb.parse_github_url(self.asset.readme_url)
                if parsed_url:
                    repo_info = gb.get_repository(parsed_url["owner"], parsed_url["repo"])
                    if repo_info:
                        logger.debug(
                            f"Repository {parsed_url['owner']}/{parsed_url['repo']} is accessible. "
                            f"Private: {repo_info.get('private', 'unknown')}"
                        )
                    else:
                        logger.warning(
                            f"Repository {parsed_url['owner']}/{parsed_url['repo']} is not accessible "
                            f"with current credentials"
                        )

                # Now check if the specific file exists
                if not gb.file_exists(self.asset.readme_url):
                    self.error(
                        AssetErrorLogType.INVALID_README_URL,
                        f"Readme URL points to a missing file: {self.asset.readme_url}",
                    )
            except GithubAuthException:
                self.error(
                    AssetErrorLogType.INVALID_OWNER,
                    "Cannot connect to github to validate readme url, please fix owner or credentials",
                )
            except Exception as e:
                # Log the error with more context for debugging
                error_str = str(e).lower()
                logger.warning(f"Could not validate readme URL {self.asset.readme_url}: {str(e)}")

                # Only fail validation for clear 404 errors (file definitely doesn't exist)
                if "404" in error_str or "not found" in error_str:
                    self.error(
                        AssetErrorLogType.INVALID_README_URL,
                        f"Readme URL points to a missing file: {self.asset.readme_url}",
                    )

                # For 403/401 errors or other issues with private repos, log but don't fail validation
                elif "403" in error_str or "forbidden" in error_str:
                    logger.info(
                        f"Access forbidden for readme URL {self.asset.readme_url}. "
                        f"This might be a private repository that the credentials don't have access to."
                    )
                elif "401" in error_str or "unauthorized" in error_str:
                    logger.warning(
                        f"Authentication failed for readme URL {self.asset.readme_url}. "
                        f"GitHub credentials might be invalid or expired."
                    )
                else:
                    logger.warning(f"Could not validate readme URL {self.asset.readme_url} due to: {str(e)}")

                # For all non-404 errors, we don't fail validation to avoid false negatives

    def urls(self):

        readme = self.asset.get_readme(parse=True)
        if "html" in readme:
            urls = get_urls_from_html(readme["html"])
            for url in urls:
                try:
                    # Skip validation for trusted URLs
                    if is_trusted_url(url):
                        print(f"✅ Skipping validation for trusted URL: {url}")
                        continue

                    # Skip test_url for internal GitHub repository URLs
                    if is_internal_github_url(url, self.asset.readme_url):
                        print(f"🔍 Validating internal GitHub URL: {url}")
                        # Internal URLs will be validated using GitHub API instead
                        self._validate_internal_github_url(url)
                        continue

                    test_url(url, allow_relative=False)
                except Exception as e:
                    self.error(AssetErrorLogType.INVALID_URL, str(e))
                    raise AssetException(str(e), severity="ERROR")

    def _validate_internal_github_url(self, url):
        """
        Validate internal GitHub URLs using the GitHub API.
        Only validates if the asset has an owner with GitHub credentials.
        Handles various GitHub URL patterns:
        - github.com/org/repo/blob/branch/path
        - raw.githubusercontent.com/org/repo/branch/path
        - github.com/org/repo/issues/number
        - github.com/org/repo/pulls/number
        - etc.
        """
        if not self.asset.owner:
            # If no owner, we can't validate through GitHub API, just skip silently
            return

        credentials = CredentialsGithub.objects.filter(user=self.asset.owner).first()
        if credentials is None:
            # If no GitHub credentials, we can't validate through GitHub API, just skip silently
            return

        gb = Github(credentials.token)
        try:
            # Check if URL points to a file that can be validated
            if self._is_github_file_url(url):
                # For file URLs (blob, raw), check if the file exists
                if not gb.file_exists(url):
                    raise Exception(f"Internal GitHub file not found: {url}")
            # For other internal URLs (issues, PRs, discussions, etc.), we assume they're valid
            # since they point to the same repository and we can't easily validate them via API
            # without making additional requests
        except GithubAuthException:
            # If we can't authenticate with GitHub, just skip validation
            # rather than failing the entire validation
            logger.warning(f"GitHub authentication failed when validating internal URL: {url}")
            pass
        except Exception as e:
            # Handle different types of errors more gracefully
            error_str = str(e).lower()

            # Only fail for clear 404 errors (file definitely doesn't exist)
            if "404" in error_str or "not found" in error_str:
                raise Exception(f"Internal GitHub file not found: {url}")

            # For access/auth issues with private repos, log but don't fail
            elif "403" in error_str or "forbidden" in error_str:
                logger.info(
                    f"Access forbidden for internal GitHub URL: {url}. "
                    f"This might be a private repository access issue."
                )
            elif "401" in error_str or "unauthorized" in error_str:
                logger.warning(
                    f"Authentication failed for internal GitHub URL: {url}. " f"GitHub credentials might be invalid."
                )
            else:
                # For other errors, log the issue but don't fail validation
                logger.warning(f"Could not validate internal GitHub URL {url}: {str(e)}")

            # Don't re-raise for non-404 errors to avoid failing validation on private repo access issues

    def _is_github_file_url(self, url):
        """
        Check if a GitHub URL points to a file that can be validated.
        Returns True for URLs that point to actual files (blob, raw content).
        Uses the Github service's parse_github_url method to avoid code duplication.
        """
        if not url:
            return False

        # Use Github service to parse the URL (we don't need authentication for parsing)
        github_service = Github()
        parsed = github_service.parse_github_url(url)

        if not parsed:
            return False

        # Return True for URL types that point to actual files
        return parsed["url_type"] in ["blob", "raw", "api"] and parsed.get("path")

    def lang(self):

        if self.asset.lang is None or self.asset.lang == "":
            self.error(
                AssetErrorLogType.INVALID_LANGUAGE, "Asset is missing a language or has an invalid language assigned"
            )

    def translations(self):
        if self.asset.all_translations.exists() == 0:
            self.warning(AssetErrorLogType.MISSING_TRANSLATIONS, "No translations")

    def technologies(self):
        if self.asset.technologies.count() < 2:
            self.error(AssetErrorLogType.MISSING_TECHNOLOGIES, "Asset should have at least 2 technology tags")

    def difficulty(self):
        if not self.asset.difficulty:
            self.error(AssetErrorLogType.MISSING_DIFFICULTY, "Asset is missing a difficulty")

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

    def __init__(self, _asset, log_errors=False, reset_errors=False):
        super().__init__(_asset, log_errors, reset_errors)


class ArticleValidator(AssetValidator):
    warns = []
    errors = ["readme"]

    def __init__(self, _asset, log_errors=False, reset_errors=False):
        super().__init__(_asset, log_errors, reset_errors)


class StarterValidator(AssetValidator):
    warns = []
    errors = ["readme"]

    def __init__(self, _asset, log_errors=False, reset_errors=False):
        super().__init__(_asset, log_errors, reset_errors)


class ExerciseValidator(AssetValidator):
    warns = ["difficulty"]
    errors = ["readme", "preview"]

    def __init__(self, _asset, log_errors=False, reset_errors=False):
        super().__init__(_asset, log_errors, reset_errors)


class ProjectValidator(ExerciseValidator):
    warns = ["difficulty"]
    errors = ["readme", "preview"]

    def __init__(self, _asset, log_errors=False, reset_errors=False):
        super().__init__(_asset, log_errors, reset_errors)


class QuizValidator(AssetValidator):
    warns = ["difficulty"]
    errors = ["preview"]

    def __init__(self, _asset, log_errors=False, reset_errors=False):
        super().__init__(_asset, log_errors, reset_errors)


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
