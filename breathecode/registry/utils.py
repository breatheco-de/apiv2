"""
Registry utility functions for asset validation.

This module includes a trusted URL system that allows skipping validation for specific domains
and URLs that are known to be reliable but may have intermittent connectivity issues.

The trusted URL system supports:
- Trusted domains: Any URL from these domains will be skipped
- Trusted URLs: Specific URLs (ignoring query strings) that will be skipped

Configuration is done through TRUSTED_DOMAINS and TRUSTED_URLS sets in breathecode.utils.url_validator.
"""

import logging
import re
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup

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
    INVALID_LANGUAGE = "invalid-language"
    INVALID_README_URL = "invalid-readme-url"
    INVALID_IMAGE = "invalid-image"
    README_SYNTAX = "readme-syntax-error"
    INVALID_TELEMETRY = "invalid-telemetry"


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
    errors = ["readme", "preview", "telemetry"]

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
            raise Exception("Could not parse GitHub URL")

        owner = url_info["owner"]
        repo = url_info["repo"]
        branch = url_info.get("branch", "main")
        file_path = url_info.get("path")

        if not file_path:
            raise Exception("URL must point to a specific file")

        # Check repo access
        if not self.github_service.repo_exists(owner, repo):
            raise Exception(f"Repository {owner}/{repo} not found or not accessible")

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
            raise Exception(f"File not found at {file_path}")

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
        Extract metadata from learn.json configuration.
        
        Args:
            config: Parsed learn.json configuration
            metadata: Dictionary to populate with extracted metadata
        """
        if "title" in config:
            if isinstance(config["title"], str):
                metadata["title"] = config["title"]
            elif isinstance(config["title"], dict):
                # Multi-language title
                metadata["title"] = config["title"].get("en") or config["title"].get("us")

        if "description" in config:
            if isinstance(config["description"], str):
                metadata["description"] = config["description"]
            elif isinstance(config["description"], dict):
                metadata["description"] = config["description"].get("en") or config["description"].get("us")

        if "difficulty" in config:
            metadata["difficulty"] = config["difficulty"]

        if "duration" in config:
            metadata["duration"] = config["duration"]

        if "technologies" in config:
            metadata["technologies"] = config["technologies"]

        if "slug" in config:
            metadata["slug"] = config["slug"]

        if "preview" in config:
            metadata["preview"] = config["preview"]

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
        COMMON_LANGUAGES = ['en', 'us', 'es', 'pt', 'fr', 'de', 'it', 'zh', 'ja', 'ko', 'ru', 'ar']
        
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
        for lang in COMMON_LANGUAGES:
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
        COMMON_LANGUAGES = ['en', 'us', 'es', 'pt', 'fr', 'de', 'it', 'zh', 'ja', 'ko', 'ru', 'ar']
        
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
        for lang in COMMON_LANGUAGES:
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
