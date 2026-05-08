"""
Registry utility functions for asset validation.

This module includes a trusted URL system that allows skipping validation for specific domains
and URLs that are known to be reliable but may have intermittent connectivity issues.

The trusted URL system supports:
- Trusted domains: Any URL from these domains will be skipped
- Trusted URLs: Specific URLs (ignoring query strings) that will be skipped

Configuration is done through TRUSTED_DOMAINS and TRUSTED_URLS sets in breathecode.utils.url_validator.

Also includes helpers for ``Asset.github_activity_log`` (JSON array of recent GitHub-related events).
"""

from __future__ import annotations

import json
import logging
import os
import re
import requests
from typing import Any
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from django.db import transaction
from django.utils import timezone

from breathecode.authenticate.models import CredentialsGithub
from breathecode.services.github import Github, GithubAuthException

# Import URL validation utilities from shared location
from breathecode.utils.url_validator import (
    TRUSTED_DOMAINS,
    TRUSTED_URLS,
    normalize_url_for_comparison,
    is_trusted_url,
    get_trusted_domains,
    get_trusted_urls,
    test_url,
    atest_url,
)

logger = logging.getLogger(__name__)


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
    INVALID_SLUG_REFERENCE = "invalid-slug-reference"
    INVALID_LANGUAGE = "invalid-language"
    INVALID_README_URL = "invalid-readme-url"
    INVALID_IMAGE = "invalid-image"
    README_SYNTAX = "readme-syntax-error"
    INVALID_TELEMETRY = "invalid-telemetry"
    INVALID_TEMPLATE_SUBDIRECTORY = "invalid-template-subdirectory"
    MISSING_PREVIEW = "missing-preview"


ASSET_ERROR_LOG_CATALOG_METADATA = {
    AssetErrorLogType.SLUG_NOT_FOUND: {
        "label": "Slug not found",
        "description": "The requested asset slug does not exist as an asset or alias.",
        "common_trigger_situations": [
            "A request uses a slug that does not exist in registry.",
            "A link points to an outdated or mistyped slug.",
        ],
        "severity_hint": "high",
        "status_notes": "Set FIXED after creating a valid alias or correcting the source slug.",
    },
    AssetErrorLogType.DIFFERENT_TYPE: {
        "label": "Different asset type",
        "description": "The requested slug exists but does not match the expected asset_type.",
        "common_trigger_situations": [
            "A consumer expects LESSON but slug points to PROJECT.",
            "An integration hardcodes the wrong asset_type for a valid slug.",
        ],
        "severity_hint": "medium",
        "status_notes": "Set FIXED after correcting requested type or canonicalizing route usage.",
    },
    AssetErrorLogType.EMPTY_README: {
        "label": "Empty readme",
        "description": "The asset readme content is missing or empty.",
        "common_trigger_situations": [
            "Readme was not found during readme loading.",
            "Asset was created without a readme file configured.",
        ],
        "severity_hint": "high",
        "status_notes": "Set FIXED after uploading/syncing a valid readme.",
    },
    AssetErrorLogType.EMPTY_CATEGORY: {
        "label": "Empty category",
        "description": "The asset or referenced asset is missing category association.",
        "common_trigger_situations": [
            "Readme reference rewrite resolves an asset without category.",
            "Validation runs on assets with null category.",
        ],
        "severity_hint": "medium",
        "status_notes": "Set FIXED after assigning a valid category.",
    },
    AssetErrorLogType.INVALID_OWNER: {
        "label": "Invalid owner",
        "description": "Owner requirements failed for GitHub/readme operations.",
        "common_trigger_situations": [
            "Asset has no owner when readme validation requires one.",
            "Owner exists but has no GitHub credentials.",
        ],
        "severity_hint": "high",
        "status_notes": "Set FIXED after assigning owner and valid GitHub credentials.",
    },
    AssetErrorLogType.MISSING_TECHNOLOGIES: {
        "label": "Missing technologies",
        "description": "Asset is missing required technology tags.",
        "common_trigger_situations": [
            "Validation finds less than minimum required technologies.",
        ],
        "severity_hint": "low",
        "status_notes": "Set FIXED after adding the required technology tags.",
    },
    AssetErrorLogType.MISSING_DIFFICULTY: {
        "label": "Missing difficulty",
        "description": "Asset has no difficulty value configured.",
        "common_trigger_situations": [
            "Validation runs on assets missing difficulty metadata.",
        ],
        "severity_hint": "low",
        "status_notes": "Set FIXED after assigning a valid difficulty level.",
    },
    AssetErrorLogType.MISSING_TRANSLATIONS: {
        "label": "Missing translations",
        "description": "Asset has no translations where expected.",
        "common_trigger_situations": [
            "Validation checks translation coverage and finds none.",
        ],
        "severity_hint": "low",
        "status_notes": "Can remain IGNORED for intentionally single-language content.",
    },
    AssetErrorLogType.POOR_DESCRIPTION: {
        "label": "Poor description",
        "description": "Asset description is empty or too short.",
        "common_trigger_situations": [
            "Validation checks description quality and minimum length.",
        ],
        "severity_hint": "low",
        "status_notes": "Set FIXED after improving description content.",
    },
    AssetErrorLogType.EMPTY_HTML: {
        "label": "Empty HTML",
        "description": "Rendered asset HTML response was empty.",
        "common_trigger_situations": [
            "A request asks for rendered HTML but result is empty.",
        ],
        "severity_hint": "medium",
        "status_notes": "Set FIXED after restoring valid readme rendering/output.",
    },
    AssetErrorLogType.INVALID_URL: {
        "label": "Invalid URL",
        "description": "A URL required by asset delivery or validation is invalid or unreachable.",
        "common_trigger_situations": [
            "Asset redirect URL validation fails in forward routes.",
            "URL testing fails during validation.",
        ],
        "severity_hint": "high",
        "status_notes": "Set FIXED after correcting broken URL and confirming accessibility.",
    },
    AssetErrorLogType.INVALID_SLUG_REFERENCE: {
        "label": "Invalid slug reference",
        "description": "A readme asset reference points to an unknown slug.",
        "common_trigger_situations": [
            'Readme link pattern `[text]{ref="slug"}` references missing asset/alias.',
        ],
        "severity_hint": "medium",
        "status_notes": "Set FIXED after updating readme reference or creating alias.",
    },
    AssetErrorLogType.INVALID_LANGUAGE: {
        "label": "Invalid language",
        "description": "Asset language is missing or invalid.",
        "common_trigger_situations": [
            "Validation runs with null/unsupported language code.",
        ],
        "severity_hint": "medium",
        "status_notes": "Set FIXED after assigning a supported language.",
    },
    AssetErrorLogType.INVALID_README_URL: {
        "label": "Invalid readme URL",
        "description": "Readme URL extension or format is not supported.",
        "common_trigger_situations": [
            "Readme URL does not end in supported extension (.md, .mdx, .txt, .ipynb).",
            "Readme URL parsing fails during readme processing.",
        ],
        "severity_hint": "high",
        "status_notes": "Set FIXED after pointing readme_url to a supported file.",
    },
    AssetErrorLogType.INVALID_IMAGE: {
        "label": "Invalid image",
        "description": "Image URL in asset content is invalid or not accessible.",
        "common_trigger_situations": [
            "Validation of image resources fails URL checks or request tests.",
        ],
        "severity_hint": "low",
        "status_notes": "Set FIXED after replacing broken image URLs.",
    },
    AssetErrorLogType.README_SYNTAX: {
        "label": "Readme syntax error",
        "description": "Readme contains malformed hide-comment markers.",
        "common_trigger_situations": [
            "Odd number of `<!-- hide -->` / `<!-- endhide -->` markers.",
        ],
        "severity_hint": "medium",
        "status_notes": "Set FIXED after correcting hide comment pairs.",
    },
    AssetErrorLogType.INVALID_TELEMETRY: {
        "label": "Invalid telemetry",
        "description": "Asset telemetry configuration is malformed or inconsistent.",
        "common_trigger_situations": [
            "Telemetry JSON/schema checks fail during validation.",
        ],
        "severity_hint": "medium",
        "status_notes": "Set FIXED after aligning telemetry config with expected schema.",
    },
    AssetErrorLogType.INVALID_TEMPLATE_SUBDIRECTORY: {
        "label": "Invalid template subdirectory",
        "description": "Template subdirectory points to a missing or invalid location.",
        "common_trigger_situations": [
            "Template subdirectory validation fails for project/exercise setup.",
        ],
        "severity_hint": "medium",
        "status_notes": "Set FIXED after correcting template subdirectory path.",
    },
    AssetErrorLogType.MISSING_PREVIEW: {
        "label": "Missing preview",
        "description": "Asset preview image/URL is missing where expected.",
        "common_trigger_situations": [
            "Asset sync or preview generation step detects absent preview.",
        ],
        "severity_hint": "low",
        "status_notes": "Set FIXED after setting preview and revalidating asset.",
    },
}


def get_asset_error_log_catalog():
    catalog = []
    default_metadata = {
        "label": "Unknown error",
        "description": "No description documented yet for this error type.",
        "common_trigger_situations": [],
        "severity_hint": "unknown",
        "status_notes": "Use FIXED when resolved, or IGNORED if accepted as known condition.",
    }

    for attr_name in dir(AssetErrorLogType):
        if attr_name.startswith("_"):
            continue

        slug = getattr(AssetErrorLogType, attr_name)
        if not isinstance(slug, str):
            continue

        metadata = {**default_metadata, **ASSET_ERROR_LOG_CATALOG_METADATA.get(slug, {})}
        catalog.append({"slug": slug, **metadata})

    catalog.sort(key=lambda item: item["slug"])
    return catalog


def compute_asset_error_log_dedupe_merge(keeper, duplicate_rows):
    """
    Merge duplicate AssetErrorLog rows into a single keeper row.

    This is intentionally pure (no DB access) so it can be unit-tested without
    relying on being able to insert duplicate rows in environments that enforce
    uniqueness constraints at the database layer.
    """

    status_rank = {"ERROR": 3, "FIXED": 2, "IGNORED": 1}
    merged_status = max([keeper.status] + [row.status for row in duplicate_rows], key=lambda s: status_rank.get(s, 0))

    merged_status_text = keeper.status_text
    if not merged_status_text:
        for row in reversed(duplicate_rows):
            if getattr(row, "status_text", None):
                merged_status_text = row.status_text
                break

    merged_user_id = keeper.user_id
    if not merged_user_id:
        for row in reversed(duplicate_rows):
            if getattr(row, "user_id", None):
                merged_user_id = row.user_id
                break

    merged_priority = keeper.priority
    for row in duplicate_rows:
        merged_priority = max(merged_priority, row.priority)

    update_fields = []
    if keeper.status != merged_status:
        update_fields.append("status")

    if keeper.status_text != merged_status_text:
        update_fields.append("status_text")

    if keeper.user_id != merged_user_id:
        update_fields.append("user")

    if keeper.priority != merged_priority:
        update_fields.append("priority")

    return {
        "status": merged_status,
        "status_text": merged_status_text,
        "user_id": merged_user_id,
        "priority": merged_priority,
        "update_fields": update_fields,
    }


def get_base_path_from_readme_url(readme_url):
    """
    Extract the base path (subdirectory) from a GitHub readme_url.

    For .../blob/<branch>/README.md returns "" (root).
    For .../blob/<branch>/projects/myproject/README.md returns "projects/myproject".

    Returns:
        str: The directory path, or "" if at repo root or URL has no path.
    """
    if not readme_url:
        return ""
    match = re.search(r"\/blob\/([\w\d_\-]+)\/(.+)", readme_url)
    if not match:
        return ""
    _branch, path = match.groups()
    base_path = os.path.dirname(path)
    return base_path.strip("/") if base_path else ""


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


# test_url, atest_url, and related functions are now imported from breathecode.utils.url_validator


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

    def telemetry(self):
        """
        Validate that if telemetry.batch exists in config, the URL contains the correct asset_id.
        """
        if not self.asset.config:
            return

        # Check if telemetry exists in config
        telemetry = self.asset.config.get("telemetry")
        if not telemetry:
            return

        # Check if batch URL exists
        batch_url = telemetry.get("batch")
        if not batch_url:
            return

        # Parse the URL to extract query parameters
        try:
            parsed_url = urlparse(batch_url)
            
            # Extract query parameters
            from urllib.parse import parse_qs
            query_params = parse_qs(parsed_url.query)
            
            # Check if asset_id parameter exists
            if "asset_id" not in query_params:
                self.error(
                    AssetErrorLogType.INVALID_TELEMETRY,
                    f"Telemetry batch URL is missing asset_id parameter: {batch_url}",
                )
                return
            
            # Get the asset_id from the URL (parse_qs returns lists)
            url_asset_id = query_params["asset_id"][0]
            
            # Convert to int for comparison
            try:
                url_asset_id_int = int(url_asset_id)
            except ValueError:
                self.error(
                    AssetErrorLogType.INVALID_TELEMETRY,
                    f"Telemetry batch URL has invalid asset_id format: {url_asset_id}",
                )
                return
            
            # Check if asset_id matches the actual asset id
            if url_asset_id_int != self.asset.id:
                self.error(
                    AssetErrorLogType.INVALID_TELEMETRY,
                    f"Telemetry batch URL has incorrect asset_id. Expected {self.asset.id}, got {url_asset_id_int}",
                )
                
        except Exception as e:
            self.error(
                AssetErrorLogType.INVALID_TELEMETRY,
                f"Error validating telemetry batch URL: {str(e)}",
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
    errors = ["readme", "preview", "telemetry"]

    def __init__(self, _asset, log_errors=False, reset_errors=False):
        super().__init__(_asset, log_errors, reset_errors)


class ProjectValidator(ExerciseValidator):
    warns = ["difficulty"]
    errors = ["readme", "preview", "telemetry", "template_subdirectory"]

    def __init__(self, _asset, log_errors=False, reset_errors=False):
        super().__init__(_asset, log_errors, reset_errors)

    def template_subdirectory(self):
        """
        For PROJECTs in a subdirectory: template in learn.json cannot be "self";
        if set, it must be a URL (template repo). Enforced as part of asset integrity test.
        """
        if self.asset.asset_type != "PROJECT":
            return
        base_path = get_base_path_from_readme_url(self.asset.readme_url)
        if not base_path:
            return
        template_url = (self.asset.template_url or "").strip()
        if template_url == "self":
            self.error(
                AssetErrorLogType.INVALID_TEMPLATE_SUBDIRECTORY,
                "For projects in a subdirectory, template in learn.json cannot be 'self'; "
                "if set, it must be a URL (e.g. a template repo).",
            )
        if template_url and template_url != "self" and not is_url(template_url):
            self.error(
                AssetErrorLogType.INVALID_TEMPLATE_SUBDIRECTORY,
                "For projects in a subdirectory, template in learn.json must be a valid URL when set.",
            )


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


class AssetParser:
    """
    Utility class for parsing and extracting metadata from GitHub asset URLs.
    
    This class helps identify asset types (QUIZ, LESSON, EXERCISE, PROJECT) and
    extract metadata from their content without creating database records.
    
    Usage:
        parser = AssetParser(github_token)
        metadata = parser.parse_readme_url(url)
    """

    def __init__(self, github_token):
        """
        Initialize the parser with a GitHub token for API access.
        
        Args:
            github_token: GitHub personal access token for API authentication
        """
        from breathecode.services.github import Github as GithubService

        self.github_service = GithubService(token=github_token)
        self.token = github_token

    def parse_readme_url(self, readme_url):
        """
        Parse a GitHub readme URL and extract all available metadata.
        
        Args:
            readme_url: GitHub URL pointing to a markdown or JSON file
            
        Returns:
            dict: Metadata including asset_type, title, description, etc.
            
        Raises:
            Exception: If URL is invalid or content cannot be fetched
        """
        # Parse the URL
        url_info = self.github_service.parse_github_url(readme_url)
        if not url_info:
            raise Exception(
                "Expected a GitHub URL pointing to a repository file "
                f"(for example: https://github.com/owner/repo/blob/branch/path/to/file), "
                f"but received '{readme_url}', which could not be parsed."
            )

        owner = url_info["owner"]
        repo = url_info["repo"]
        branch = url_info.get("branch", "main")
        file_path = url_info.get("path")

        if not file_path:
            raise Exception(
                "Expected the GitHub URL to point to a specific file including branch and path "
                f"(for example: https://github.com/{owner}/{repo}/blob/{branch}/path/to/file), "
                f"but received a URL that resolves to the repository or a directory instead: '{readme_url}'."
            )

        # Check repo access
        if not self.github_service.repo_exists(owner, repo):
            raise Exception(
                f"Expected repository '{owner}/{repo}' to be accessible to read asset metadata, "
                "but GitHub reported that it does not exist or cannot be accessed with the current credentials. "
                "Verify the repository name, visibility, and permissions for the token/user being used."
            )

        # Initialize metadata
        metadata = {
            "readme_url": readme_url,
            "url": f"https://github.com/{owner}/{repo}",
            "owner": owner,
            "repo": repo,
            "branch": branch,
            "file_path": file_path,
        }

        # Fetch file content
        response = self.github_service.get(f"/repos/{owner}/{repo}/contents/{file_path}?ref={branch}")

        if not response or response.get("type") != "file":
            raise Exception(
                f"Expected a file at path '{file_path}' in repository '{owner}/{repo}' on branch '{branch}', "
                "but GitHub did not return a file object at that location. This usually means the path is wrong, "
                "points to a folder, or the file does not exist."
            )

        # Decode content
        import base64

        content = base64.b64decode(response["content"]).decode("utf-8")

        # Detect asset type and extract metadata
        if file_path.endswith(".json"):
            self._parse_json_asset(content, metadata, owner, repo, branch, file_path)
        elif file_path.endswith(".md"):
            self._parse_markdown_asset(content, metadata, owner, repo, branch, file_path)

        # Get repository information
        self._add_repository_info(metadata, owner, repo)

        return metadata

    def _parse_json_asset(self, content, metadata, owner, repo, branch, file_path):
        """
        Parse JSON file and determine if it's a QUIZ.
        
        Args:
            content: File content as string
            metadata: Dictionary to populate with extracted metadata
            owner: Repository owner
            repo: Repository name
            branch: Branch name
            file_path: Path to the file in the repository
        """
        import json
        import re

        try:
            config = json.loads(content)

            # Check for quiz structure (must have "info" and "questions")
            if "info" in config and "questions" in config:
                metadata["asset_type"] = "QUIZ"
                metadata["config"] = config

                # Extract quiz metadata from info section
                if "info" in config:
                    info = config["info"]

                    if "name" in info:
                        metadata["title"] = info["name"]
                    elif "title" in info:
                        metadata["title"] = info["title"]

                    if "main" in info:
                        metadata["description"] = info["main"]
                    elif "description" in info:
                        metadata["description"] = info["description"]

                    if "difficulty" in info:
                        metadata["difficulty"] = info["difficulty"]

                    if "technologies" in info:
                        metadata["technologies"] = info["technologies"]

                    if "slug" in info:
                        metadata["slug"] = info["slug"]

                    # Infer language from filename first (e.g., quiz.es.json)
                    filename = file_path.split("/")[-1]
                    lang_from_filename = self._infer_language_from_json_filename(filename)
                    
                    # Use filename language or fall back to slug pattern
                    if lang_from_filename:
                        metadata["lang"] = lang_from_filename
                    elif "slug" in info:
                        # Legacy: Infer language from slug pattern
                        if info["slug"].endswith("-es"):
                            metadata["lang"] = "es"
                        elif info["slug"].endswith("-pt"):
                            metadata["lang"] = "pt"
                        else:
                            metadata["lang"] = "en"
                    else:
                        metadata["lang"] = "en"

                    # Detect available translations for JSON quizzes
                    directory = "/".join(file_path.split("/")[:-1])
                    translations = self._detect_json_translations(owner, repo, branch, directory, filename, metadata.get("lang"))
                    if translations:
                        metadata["translations"] = translations

                # Count questions
                if "questions" in config:
                    metadata["question_count"] = len(config["questions"])
            else:
                # JSON but not a quiz structure
                metadata["asset_type"] = "UNKNOWN"
                metadata["note"] = "JSON file but doesn't match QUIZ structure (missing 'info' or 'questions')"

        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON file: {str(e)}")

    def _parse_markdown_asset(self, content, metadata, owner, repo, branch, file_path):
        """
        Parse markdown file and determine if it's a LESSON or part of an EXERCISE/PROJECT.
        
        Args:
            content: File content as string
            metadata: Dictionary to populate with extracted metadata
            owner: Repository owner
            repo: Repository name
            branch: Branch name
            file_path: Path to the file in the repository
        """
        import re

        # Check for learn.json in the same directory or .learn subdirectory
        directory = "/".join(file_path.split("/")[:-1])
        has_learn_json = self._check_for_learn_json(owner, repo, branch, directory)

        if has_learn_json:
            # Has learn.json, so it's likely an EXERCISE or PROJECT
            metadata["asset_type"] = "EXERCISE_OR_PROJECT"
            metadata["note"] = "This file is part of an EXERCISE or PROJECT (has learn.json). Use standard import flow."
            # Infer language from readme URL filename (e.g. some-name.es.md -> spanish)
            filename = file_path.split("/")[-1]
            lang = self._infer_language_from_filename(filename)
            if lang:
                metadata["lang"] = lang
            # Try to fetch and parse learn.json
            learn_config = self._fetch_learn_json(owner, repo, branch, directory)
            if learn_config:
                metadata["learn_config"] = learn_config
                self._extract_learn_json_metadata(learn_config, metadata)
        else:
            # No learn.json found, it's a LESSON
            metadata["asset_type"] = "LESSON"

            # Parse markdown frontmatter
            frontmatter = self._extract_frontmatter(content)
            if frontmatter:
                self._extract_lesson_metadata(frontmatter, metadata)

            # Infer language from filename (e.g., README.es.md, lesson.pt.md)
            filename = file_path.split("/")[-1]
            lang = self._infer_language_from_filename(filename)
            if lang:
                metadata["lang"] = lang

            # Detect available translations
            directory = "/".join(file_path.split("/")[:-1])
            translations = self._detect_translations(owner, repo, branch, directory, filename, lang)
            if translations:
                metadata["translations"] = translations

            # Extract content preview (first paragraph after frontmatter)
            content_preview = self._extract_content_preview(content)
            if content_preview:
                metadata["content_preview"] = content_preview

    def _check_for_learn_json(self, owner, repo, branch, directory):
        """
        Check if learn.json or bc.json exists in the directory.
        
        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name
            directory: Directory path to check
            
        Returns:
            bool: True if learn.json or bc.json exists
        """
        learn_json_paths = [
            f"{directory}/learn.json" if directory else "learn.json",
            f"{directory}/.learn/learn.json" if directory else ".learn/learn.json",
            f"{directory}/bc.json" if directory else "bc.json",
            f"{directory}/.learn/bc.json" if directory else ".learn/bc.json",
        ]

        for learn_path in learn_json_paths:
            try:
                response = self.github_service.get(f"/repos/{owner}/{repo}/contents/{learn_path}?ref={branch}")
                if response and response.get("type") == "file":
                    return True
            except Exception:
                continue

        return False

    def _fetch_learn_json(self, owner, repo, branch, directory):
        """
        Fetch and parse learn.json or bc.json if it exists.
        
        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name
            directory: Directory path to check
            
        Returns:
            dict: Parsed JSON config or None if not found
        """
        import base64
        import json

        learn_json_paths = [
            f"{directory}/learn.json" if directory else "learn.json",
            f"{directory}/.learn/learn.json" if directory else ".learn/learn.json",
            f"{directory}/bc.json" if directory else "bc.json",
            f"{directory}/.learn/bc.json" if directory else ".learn/bc.json",
        ]

        for learn_path in learn_json_paths:
            try:
                response = self.github_service.get(f"/repos/{owner}/{repo}/contents/{learn_path}?ref={branch}")
                if response and response.get("type") == "file":
                    content = base64.b64decode(response["content"]).decode("utf-8")
                    return json.loads(content)
            except Exception:
                continue

        return None

    def _extract_learn_json_metadata(self, config, metadata):
        """
        Extract metadata from learn.json configuration using canonical Asset mapping.
        """
        from breathecode.registry.models import Asset

        extracted = Asset.learn_config_to_metadata(config, metadata.get("lang"))
        metadata.update(extracted)

    def _extract_frontmatter(self, content):
        """
        Extract YAML frontmatter from markdown content.
        
        Args:
            content: Markdown content as string
            
        Returns:
            dict: Parsed frontmatter or None if not found
        """
        import re

        frontmatter_match = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL)

        if frontmatter_match:
            try:
                import yaml

                return yaml.safe_load(frontmatter_match.group(1))
            except Exception as e:
                logger.warning(f"Could not parse frontmatter: {str(e)}")

        return None

    def _extract_lesson_metadata(self, frontmatter, metadata):
        """
        Extract metadata from lesson markdown frontmatter.
        
        Args:
            frontmatter: Parsed YAML frontmatter
            metadata: Dictionary to populate with extracted metadata
        """
        if "title" in frontmatter:
            metadata["title"] = frontmatter["title"]

        if "excerpt" in frontmatter:
            metadata["description"] = frontmatter["excerpt"]
        elif "description" in frontmatter:
            metadata["description"] = frontmatter["description"]
        elif "subtitle" in frontmatter:
            metadata["description"] = frontmatter["subtitle"]

        if "authors" in frontmatter:
            metadata["authors"] = frontmatter["authors"]

        if "tags" in frontmatter and isinstance(frontmatter["tags"], list):
            metadata["technologies"] = frontmatter["tags"]
        elif "technologies" in frontmatter and isinstance(frontmatter["technologies"], list):
            metadata["technologies"] = frontmatter["technologies"]

        if "video" in frontmatter:
            metadata["intro_video_url"] = frontmatter["video"]

        if "table_of_contents" in frontmatter:
            metadata["enable_table_of_content"] = frontmatter["table_of_contents"]

        if "slug" in frontmatter:
            metadata["slug"] = frontmatter["slug"]

        if "difficulty" in frontmatter:
            metadata["difficulty"] = frontmatter["difficulty"]

    def _infer_language_from_filename(self, filename):
        """
        Infer language code from filename pattern.
        Supports patterns like:
        - README.es.md -> 'es'
        - lesson.pt.md -> 'pt'
        - tutorial.fr.md -> 'fr'
        - README.us.md -> 'en' (us is aliased to en)
        - README.md -> 'en' (default)
        - any-file.md -> 'en' (default)
        
        Args:
            filename: Name of the file
            
        Returns:
            str: Language code (e.g., 'es', 'pt', 'fr') or 'en' as default, or None if not a markdown file
        """
        import re

        # Only process markdown files
        if not filename.lower().endswith('.md'):
            return None

        # Pattern: ANY_FILENAME.{lang}.md (e.g., README.es.md, lesson.pt.md, tutorial.fr.md)
        lang_match = re.search(r'\.([a-z]{2})\.md$', filename, re.IGNORECASE)
        if lang_match:
            lang = lang_match.group(1).lower()
            # Alias 'us' to 'en'
            return 'en' if lang == 'us' else lang

        # Default to English for any .md file without language code
        return "en"

    def _detect_translations(self, owner, repo, branch, directory, filename, current_lang):
        """
        Detect available translations by checking for language variants of the same file.
        For example, if current file is README.es.md, checks for README.md, README.pt.md, README.fr.md, etc.
        
        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name
            directory: Directory path
            filename: Current filename
            current_lang: Current detected language code
            
        Returns:
            list: List of available language codes (excluding current language)
        """
        import re
        
        # Common language codes to check (us is included as it's aliased to en in filenames)
        common_languages = ['en', 'us', 'es', 'pt', 'fr', 'de', 'it', 'zh', 'ja', 'ko', 'ru', 'ar']
        
        # Extract base filename without language code
        # e.g., "README.es.md" -> "README", "lesson.pt.md" -> "lesson"
        base_name = re.sub(r'\.[a-z]{2}\.md$', '', filename, flags=re.IGNORECASE)
        if not base_name.endswith('.md'):
            base_name += '.md'  # For files like "README.md" where base is already the full name
        else:
            # filename was like "README.md", so base_name would be "README.md"
            # we need to remove .md to get just "README"
            base_name = base_name[:-3]
        
        available_translations = []
        
        # Check for each language variant
        for lang in common_languages:
            if lang == current_lang:
                continue  # Skip current language
            
            # Build the filename to check
            if lang == 'en':
                # English is typically the base file without language code
                test_filename = f"{base_name}.md"
            else:
                # Other languages have the language code
                test_filename = f"{base_name}.{lang}.md"
            
            # Build full path
            if directory:
                test_path = f"{directory}/{test_filename}"
            else:
                test_path = test_filename
            
            # Check if file exists
            try:
                response = self.github_service.get(f"/repos/{owner}/{repo}/contents/{test_path}?ref={branch}")
                if response and response.get("type") == "file":
                    available_translations.append(lang)
            except Exception:
                continue
        
        return available_translations if available_translations else None

    def _infer_language_from_json_filename(self, filename):
        """
        Infer language code from JSON filename pattern.
        Supports patterns like:
        - quiz.es.json -> 'es'
        - test.pt.json -> 'pt'
        - quiz.us.json -> 'en' (us is aliased to en)
        - quiz.json -> 'en' (default)
        
        Args:
            filename: Name of the file
            
        Returns:
            str: Language code (e.g., 'es', 'pt') or 'en' as default, or None if not a JSON file
        """
        import re

        # Only process JSON files
        if not filename.lower().endswith('.json'):
            return None

        # Pattern: ANY_FILENAME.{lang}.json (e.g., quiz.es.json, test.pt.json)
        lang_match = re.search(r'\.([a-z]{2})\.json$', filename, re.IGNORECASE)
        if lang_match:
            lang = lang_match.group(1).lower()
            # Alias 'us' to 'en'
            return 'en' if lang == 'us' else lang

        # Default to English for any .json file without language code
        return "en"

    def _detect_json_translations(self, owner, repo, branch, directory, filename, current_lang):
        """
        Detect available translations for JSON quiz files.
        For example, if current file is quiz.es.json, checks for quiz.json, quiz.pt.json, etc.
        
        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name
            directory: Directory path
            filename: Current filename
            current_lang: Current detected language code
            
        Returns:
            list: List of available language codes (excluding current language)
        """
        import re
        
        # Common language codes to check (us is included as it's aliased to en in filenames)
        common_languages = ['en', 'us', 'es', 'pt', 'fr', 'de', 'it', 'zh', 'ja', 'ko', 'ru', 'ar']
        
        # Extract base filename without language code
        # e.g., "quiz.es.json" -> "quiz", "test.pt.json" -> "test"
        base_name = re.sub(r'\.[a-z]{2}\.json$', '', filename, flags=re.IGNORECASE)
        if not base_name.endswith('.json'):
            base_name += '.json'  # For files like "quiz.json" where base is already the full name
        else:
            # filename was like "quiz.json", so base_name would be "quiz.json"
            # we need to remove .json to get just "quiz"
            base_name = base_name[:-5]
        
        available_translations = []
        
        # Check for each language variant
        for lang in common_languages:
            if lang == current_lang:
                continue  # Skip current language
            
            # Build the filename to check
            if lang == 'en':
                # English is typically the base file without language code
                test_filename = f"{base_name}.json"
            else:
                # Other languages have the language code
                test_filename = f"{base_name}.{lang}.json"
            
            # Build full path
            if directory:
                test_path = f"{directory}/{test_filename}"
            else:
                test_path = test_filename
            
            # Check if file exists
            try:
                response = self.github_service.get(f"/repos/{owner}/{repo}/contents/{test_path}?ref={branch}")
                if response and response.get("type") == "file":
                    available_translations.append(lang)
            except Exception:
                continue
        
        return available_translations if available_translations else None

    def _extract_content_preview(self, content):
        """
        Extract first paragraph from markdown content (excluding frontmatter).
        
        Args:
            content: Markdown content as string
            
        Returns:
            str: First paragraph (max 200 chars) or None
        """
        import re

        # Remove frontmatter
        content_without_frontmatter = re.sub(r"^---\s*\n.*?\n---\s*\n", "", content, flags=re.DOTALL)

        # Remove markdown headers
        content_without_headers = re.sub(r"^#+\s+.+$", "", content_without_frontmatter, flags=re.MULTILINE)

        # Get first non-empty paragraph
        paragraphs = [p.strip() for p in content_without_headers.split("\n\n") if p.strip()]

        if paragraphs:
            preview = paragraphs[0]
            # Limit to 200 characters
            if len(preview) > 200:
                preview = preview[:197] + "..."
            return preview

        return None

    def _add_repository_info(self, metadata, owner, repo):
        """
        Add repository information to metadata.
        
        Args:
            metadata: Dictionary to populate with repository info
            owner: Repository owner
            repo: Repository name
        """
        try:
            repo_info = self.github_service.get(f"/repos/{owner}/{repo}")
            if repo_info:
                metadata["is_private"] = repo_info.get("private", False)
                metadata["allow_contributions"] = not repo_info.get("private", False)
                metadata["repo_description"] = repo_info.get("description")
                metadata["repo_stars"] = repo_info.get("stargazers_count", 0)
                metadata["repo_language"] = repo_info.get("language")
        except Exception as e:
            logger.warning(f"Could not fetch repository info: {str(e)}")

    def is_quiz_json(self, json_content):
        """
        Check if JSON content matches quiz structure.
        
        Args:
            json_content: Dictionary or JSON string
            
        Returns:
            bool: True if it's a valid quiz JSON
        """
        import json

        if isinstance(json_content, str):
            try:
                json_content = json.loads(json_content)
            except json.JSONDecodeError:
                return False

        return isinstance(json_content, dict) and "info" in json_content and "questions" in json_content

    def validate_readme_url(self, url):
        """
        Validate that a URL is a valid GitHub readme URL.
        
        Args:
            url: URL to validate
            
        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        if not url:
            return False, "URL is required"

        if "github.com" not in url:
            return False, "URL must be a GitHub URL"

        url_info = self.github_service.parse_github_url(url)
        if not url_info:
            return False, "Could not parse GitHub URL"

        if not url_info.get("path"):
            return False, "URL must point to a specific file"

        return True, None


def is_internal_github_url(url, base_readme_url):
    """
    Check if a GitHub URL points to the same repository as the base readme URL.
    
    Args:
        url: URL to check
        base_readme_url: Base readme URL to compare against
        
    Returns:
        bool: True if both URLs point to the same repository
    """
    from breathecode.services.github import Github as GithubService

    github_service = GithubService()

    url_info = github_service.parse_github_url(url)
    base_info = github_service.parse_github_url(base_readme_url)

    if not url_info or not base_info:
        return False

    return url_info["owner"] == base_info["owner"] and url_info["repo"] == base_info["repo"]


# ---------------------------------------------------------------------------
# GitHub activity log (``Asset.github_activity_log``): JSON array, max 10 objects, newest first.
# ---------------------------------------------------------------------------

MAX_GITHUB_ACTIVITY_EVENTS = 10

INBOUND_WEBHOOK_STATUS_RECEIVED = "webhook_received"

KIND_HELP_TEXT: dict[str, str] = {
    "inbound_webhook": (
        "GitHub called our webhook (usually after a push to the repo). We may enqueue syncing "
        "files into this asset."
    ),
    "pull_outcome": (
        "Outcome of syncing content from GitHub into this asset, or an update linked to a "
        "prior inbound webhook."
    ),
    "academy": (
        "Something was triggered from the academy API or admin UI (pull, push, create_repo, queueing tasks, etc.). "
        "``status``: ok|error for a completed API outcome, or ``triggered`` when only the request is logged (default "
        "if omitted). ``http_status`` is the HTTP status code of our API response for that request (when known). "
        "Outcome of sync to/from GitHub is in ``pull_outcome`` / ``outbound_push``. Optional ``error``, ``detail``, "
        "``request_url``."
    ),
    "schedule_push": (
        "A push from this asset to GitHub was scheduled to run later (for example after a debounce)."
    ),
    "clear_scheduled_push": (
        "The scheduled push job is starting, or the pending scheduled push was cleared."
    ),
    "outbound_push": (
        "The application pushed content from this asset to the GitHub repository (or the attempt finished)."
    ),
    "unknown": "Unknown or legacy event type.",
}


def _kind_help_text_for(kind: str) -> str:
    return KIND_HELP_TEXT.get(kind, KIND_HELP_TEXT["unknown"])


GITHUB_ACTIVITY_REQUEST_URL_MAX_LEN = 1000


def build_request_url_for_activity_log(request: Any | None, *, max_length: int = GITHUB_ACTIVITY_REQUEST_URL_MAX_LEN) -> str | None:
    """
    Absolute URL of the current request, truncated for JSON log storage.
    Use when recording ``academy`` events from Django/DRF views or serializer context.
    """
    if request is None:
        return None
    try:
        u = request.build_absolute_uri()
        if not u:
            return None
        return str(u)[:max_length]
    except Exception:
        return None


def normalize_github_activity_log(raw: Any) -> list[dict[str, Any]]:
    """
    Returns a list of at most ``MAX_GITHUB_ACTIVITY_EVENTS`` event dicts (newest first).
    Expects ``None`` or a JSON array of objects; any other shape yields ``[]``.
    """
    if raw is None:
        return []
    if isinstance(raw, list):
        return [sure_kind(e) for e in raw if isinstance(e, dict)][:MAX_GITHUB_ACTIVITY_EVENTS]
    return []


def sure_kind(e: dict[str, Any]) -> dict[str, Any]:
    out = dict(e)
    k = out.setdefault("kind", "unknown")
    out.setdefault("kind_help_text", _kind_help_text_for(k))
    return out


def _github_activity_log_payload_for_db(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Ensure only JSON-native values before persisting. Avoids odd types and keeps the write
    path ORM-friendly (see ``_persist_github_activity_log``).
    """
    return json.loads(json.dumps(events, default=str))


def _persist_github_activity_log(asset: Any, events: list[dict[str, Any]]) -> None:
    """
    Write ``github_activity_log`` + ``updated_at`` without ``QuerySet.update``.

    Using ``.update(github_activity_log=...)`` on JSONField regressed on Django 5.x with
    ``RecursionError`` inside query compilation (``contains_aggregate``). ``bulk_update``
    matches the old behaviour of not running ``Asset.save()`` (signals / slug checks).

    Expects ``asset`` to be the locked row (e.g. from ``select_for_update``) with ``pk`` set.
    """
    from breathecode.registry.models import Asset

    asset.github_activity_log = _github_activity_log_payload_for_db(events)
    asset.updated_at = timezone.now()
    Asset.objects.bulk_update([asset], ["github_activity_log", "updated_at"])


def record_github_activity(asset_slug: str, kind: str, **kw: Any) -> None:
    """
    Appends or updates entries in ``Asset.github_activity_log`` as a JSON **array** of
    objects (max ``MAX_GITHUB_ACTIVITY_EVENTS``, newest first). Each object includes ``kind``,
    ``kind_help_text``, and ``at`` (ISO timestamp).

    **``kind`` values:** ``inbound_webhook``, ``pull_outcome``, ``academy``, ``schedule_push``,
    ``clear_scheduled_push``, ``outbound_push``. See implementation for kwargs; for ``academy`` you may pass
    ``request_url`` (e.g. from ``build_request_url_for_activity_log(request)``).

    Persistence intentionally uses ``bulk_update`` on the locked instance instead of
    ``QuerySet.update(..., github_activity_log=...)`` to avoid Django 5.x ORM recursion when
    compiling UPDATE queries over JSONField (seen on academy ``pull`` / double log writes).
    """
    from breathecode.registry.models import Asset

    def patch(events: list[dict[str, Any]]) -> None:
        now = timezone.now().isoformat()
        if kind == "inbound_webhook":
            entry: dict[str, Any] = {
                "kind": "inbound_webhook",
                "kind_help_text": _kind_help_text_for("inbound_webhook"),
                "repository_webhook_id": kw["repository_webhook_id"],
                "at": now,
                "status": kw.get("status", INBOUND_WEBHOOK_STATUS_RECEIVED),
                "commit_sha": kw["commit_sha"],
                "modified_file": kw["modified_file"],
            }
            if kw.get("detail"):
                entry["detail"] = str(kw["detail"])[:500]
            if kw.get("error"):
                entry["error"] = str(kw["error"])[:500]
            events.insert(0, entry)

        elif kind == "pull_outcome":
            success = kw["success"]
            message = kw.get("message")
            wid, csha = kw.get("repository_webhook_id"), kw.get("commit_sha")
            updated = False
            if wid is not None and csha:
                for c in events:
                    if c.get("kind") != "inbound_webhook":
                        continue
                    if c.get("repository_webhook_id") == wid and c.get("commit_sha") == csha:
                        c["pull_status"] = "ok" if success else "error"
                        if message:
                            c["pull_detail"] = str(message)[:500]
                        c["pull_finished_at"] = now
                        c["kind_help_text"] = _kind_help_text_for("inbound_webhook")
                        updated = True
                        break
            if not updated:
                events.insert(
                    0,
                    {
                        "kind": "pull_outcome",
                        "kind_help_text": _kind_help_text_for("pull_outcome"),
                        "repository_webhook_id": wid,
                        "at": now,
                        "commit_sha": csha,
                        "pull_status": "ok" if success else "error",
                        "pull_detail": (message or "")[:500],
                        "source": "pull_task",
                    },
                )

        elif kind == "schedule_push":
            events.insert(
                0,
                {
                    "kind": "schedule_push",
                    "kind_help_text": _kind_help_text_for("schedule_push"),
                    "at": now,
                    "celery_task_id": str(kw["celery_task_id"]),
                    "countdown_seconds": int(kw["countdown_seconds"]),
                },
            )

        elif kind == "clear_scheduled_push":
            events.insert(
                0,
                {
                    "kind": "clear_scheduled_push",
                    "kind_help_text": _kind_help_text_for("clear_scheduled_push"),
                    "at": now,
                },
            )

        elif kind == "outbound_push":
            events.insert(
                0,
                {
                    "kind": "outbound_push",
                    "kind_help_text": _kind_help_text_for("outbound_push"),
                    "at": now,
                    "status": "ok" if kw["success"] else "error",
                    "celery_task_id": str(kw["celery_task_id"]) if kw.get("celery_task_id") else None,
                    "detail": str(kw.get("detail") or "")[:500],
                },
            )

        elif kind == "academy":
            # Call sites usually omit status (only action + detail); avoid empty string in the payload.
            _academy_status = kw.get("status")
            if _academy_status is None or (isinstance(_academy_status, str) and not _academy_status.strip()):
                _academy_status = "triggered"
            entry_ac: dict[str, Any] = {
                "kind": "academy",
                "kind_help_text": _kind_help_text_for("academy"),
                "at": now,
                "action": kw["action"],
                "detail": str(kw.get("detail") or "")[:500],
                "status": str(_academy_status)[:16],
            }
            if kw.get("http_status") is not None:
                try:
                    entry_ac["http_status"] = int(kw["http_status"])
                except (TypeError, ValueError):
                    pass
            if kw.get("error"):
                entry_ac["error"] = str(kw["error"])[:500]
            if kw.get("exception_type"):
                entry_ac["exception_type"] = str(kw["exception_type"])[:120]
            _ru = kw.get("request_url")
            if _ru:
                entry_ac["request_url"] = str(_ru)[:GITHUB_ACTIVITY_REQUEST_URL_MAX_LEN]
            events.insert(0, entry_ac)

        else:
            logger.warning("record_github_activity: unknown kind %r", kind)

        del events[MAX_GITHUB_ACTIVITY_EVENTS:]

    try:
        with transaction.atomic():
            # Minimal columns: less work per row and only fields we read/write here.
            asset = (
                Asset.objects.select_for_update()
                .only("id", "github_activity_log")
                .filter(slug=asset_slug)
                .first()
            )
            if asset is None:
                return
            events = normalize_github_activity_log(asset.github_activity_log)
            patch(events)
            _persist_github_activity_log(asset, events)
    except Exception:
        logger.exception("record_github_activity slug=%s kind=%s", asset_slug, kind)


def log_pull_outcome_from_db(
    asset_slug: str, *, repository_webhook_id: int | None = None, commit_sha: str | None = None
) -> None:
    """After pull_from_github: reads sync_status / status_text on the asset and records pull_outcome."""
    from breathecode.registry.models import Asset

    a = Asset.objects.filter(slug=asset_slug).only("sync_status", "status_text").first()
    if not a:
        return
    ok = a.sync_status != "ERROR"
    record_github_activity(
        asset_slug,
        "pull_outcome",
        success=ok,
        message=a.status_text,
        repository_webhook_id=repository_webhook_id,
        commit_sha=commit_sha,
    )


def log_outbound_push_from_db(asset_slug: str, *, celery_task_id: str | None = None) -> None:
    """After push to GitHub: reads the asset and records outbound_push."""
    from breathecode.registry.models import Asset

    a = Asset.objects.filter(slug=asset_slug).only("sync_status", "status_text").first()
    if not a:
        return
    ok = a.sync_status != "ERROR"
    record_github_activity(
        asset_slug,
        "outbound_push",
        success=ok,
        detail=a.status_text or "",
        celery_task_id=celery_task_id,
    )
