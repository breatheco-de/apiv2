"""
URL validation utilities for validating external URLs and images.

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
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)

# Trusted domains and URLs configuration
TRUSTED_DOMAINS = {
    "exploit-db.com",
    # Add more trusted domains here as needed
    # Common domains that might have reliability issues but are trusted:
    "twitter.com",
    "x.com",
    "example.com",
    "whatsmyname.app",
    "namechk.com"
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
        normalized = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
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
        if domain.startswith("www."):
            domain = domain[4:]

        # Check if domain is in trusted domains
        if domain in TRUSTED_DOMAINS or url.startswith("http://localhost"):
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


def _shared_test_url(url, allow_relative=False, allow_hash=True):
    """
    Shared validation logic for both sync and async URL testing.
    Returns tuple (is_relative, is_hash) to indicate if network check is needed.
    """
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
    """
    Test if a URL is valid and accessible.

    Args:
        url: The URL to test
        allow_relative: Whether to allow relative URLs (e.g., ./file.html, /path/file.html)
        allow_hash: Whether to allow hash-only URLs (e.g., #section)

    Raises:
        Exception: If the URL is invalid or not accessible

    Returns:
        None if validation passes
    """
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
    """
    Async version of test_url for validating URLs in async contexts.

    Args:
        url: The URL to test
        allow_relative: Whether to allow relative URLs (e.g., ./file.html, /path/file.html)
        allow_hash: Whether to allow hash-only URLs (e.g., #section)

    Raises:
        Exception: If the URL is invalid or not accessible

    Returns:
        None if validation passes
    """
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

