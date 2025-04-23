import re
from unittest.mock import MagicMock

import pytest
import requests  # Import requests

from breathecode.registry.utils import test_url as validate_url

# Test cases: (url, allow_relative, allow_hash, head_mock_config, should_raise, match_message)
# head_mock_config: None (don't mock/expect call), status_code (int), or Exception class
test_url_cases = [
    # === Cases NOT involving requests.head ===
    ("http://example.com", False, True, 200, False, None),  # Expect success if head mock is ok
    ("https://example.com/path?query=1#frag", False, True, 200, False, None),  # Expect success
    ("//example.com/protocol-relative", False, True, 200, False, None),  # Expect success
    ("/relative/path", True, True, None, False, None),  # Relative allowed, no head call
    ("../another/relative", True, True, None, False, None),  # Relative allowed, no head call
    ("#fragment-only", True, True, None, False, None),  # Hash allowed, no head call
    ("#fragment-only", False, True, None, False, None),  # Hash allowed, no head call
    (None, False, True, None, True, "Empty url"),
    ("", False, True, None, True, "Empty url"),
    ("#fragment-only", False, False, None, True, "Not allowed hash url"),  # Hash not allowed
    ("/relative/path", False, True, None, True, "Not allowed relative url"),  # Relative not allowed
    ("../another/relative", False, True, None, True, "Not allowed relative url"),  # Relative not allowed
    # === Cases involving requests.head ===
    ("http://valid.com", False, True, 200, False, None),  # Valid URL, status 200
    ("https://redirect.com", False, True, 302, False, None),  # Valid URL, status 302
    ("http://notfound.com", False, True, 404, True, "Invalid URL with code 404"),  # Invalid status
    ("http://timeout.com", False, True, requests.exceptions.Timeout, True, "Timeout connecting to URL"),
    ("http://connerror.com", False, True, requests.exceptions.ConnectionError, True, "Connection error for URL"),
    # Example for a generic RequestException
    (
        "http://reqerror.com",
        False,
        True,
        requests.exceptions.RequestException("Some other error"),
        True,
        "Error connecting to URL.*?Some other error",
    ),
]


@pytest.mark.parametrize(
    "url, allow_relative, allow_hash, head_mock_config, should_raise, match_message",
    test_url_cases,
)
def test_validate_url(monkeypatch, url, allow_relative, allow_hash, head_mock_config, should_raise, match_message):
    """Test the test_url function with various inputs, settings, and requests.head mocks."""

    mock_head = None
    if head_mock_config is not None:
        if isinstance(head_mock_config, int):  # Simulate a status code
            mock_response = MagicMock()
            mock_response.status_code = head_mock_config
            mock_head = MagicMock(return_value=mock_response)
        else:  # Assume it's an instantiated exception (like RequestException)
            mock_head = MagicMock(side_effect=head_mock_config)

        monkeypatch.setattr(requests, "head", mock_head)

    if should_raise:
        with pytest.raises(Exception, match=match_message):
            validate_url(url, allow_relative=allow_relative, allow_hash=allow_hash)
    else:
        # Assert that no exception is raised for valid cases
        try:
            # The function itself doesn't return anything meaningful on success
            validate_url(url, allow_relative=allow_relative, allow_hash=allow_hash)
        except Exception as e:
            pytest.fail(f"test_url raised an unexpected exception: {e}")

    # Verify requests.head was called if expected
    if head_mock_config is not None and isinstance(url, str) and "//" in url:
        assert mock_head is not None
        mock_head.assert_called_once_with(url, allow_redirects=False, timeout=25)
    elif mock_head:
        mock_head.assert_not_called()


# --- Test Cases for Valid URLs (No Exception Expected) ---
valid_url_cases = [
    # ID, url, allow_relative, allow_hash, head_mock_config
    ("http_ok", "http://example.com", False, True, 200),
    ("https_ok", "https://example.com/path?query=1#frag", False, True, 200),
    # Protocol relative now requires head mock
    ("protocol_relative_ok", "//example.com/protocol-relative", False, True, 200),
    ("relative_allowed", "/relative/path", True, True, None),
    ("relative_dots_allowed", "../another/relative", True, True, None),
    ("hash_allowed_rel_true", "#fragment-only", True, True, None),
    ("hash_allowed_rel_false", "#fragment-only", False, True, None),
    # Removed "simple_string_rel_true" - will be tested as an exception case
    ("http_redirect", "https://redirect.com", False, True, 302),
]


@pytest.mark.parametrize(
    "case_id, url, allow_relative, allow_hash, head_mock_config", valid_url_cases, ids=[c[0] for c in valid_url_cases]
)
def test_valid_urls(monkeypatch, case_id, url, allow_relative, allow_hash, head_mock_config):
    """Test test_url does not raise exceptions for valid inputs and settings."""
    mock_head = None
    if head_mock_config is not None:
        mock_response = MagicMock()
        mock_response.status_code = head_mock_config
        mock_head = MagicMock(return_value=mock_response)
        monkeypatch.setattr(requests, "head", mock_head)

    try:
        validate_url(url, allow_relative=allow_relative, allow_hash=allow_hash)
    except Exception as e:
        pytest.fail(f"test_url raised an unexpected exception for case '{case_id}': {e}")

    # Adjusted check: network call happens if not relative AND not hash
    is_relative, is_hash = (False, False)  # Assume false initially
    if isinstance(url, str):
        is_relative = (
            url.startswith("../") or url.startswith("./") or (url.startswith("/") and not url.startswith("//"))
        )
        is_hash = url.startswith("#")

    url_should_trigger_head = not is_relative and not is_hash

    if mock_head:
        if url_should_trigger_head:
            # Check if scheme was auto-added if needed (crude check)
            expected_url = url
            if url.startswith("//"):
                # Requests handles protocol relative implicitly, might add https?
                # Or maybe it keeps // - this depends on requests internal handling
                # For mocking, let's assume it passes the original url
                pass
            elif not re.match(r"^[a-zA-Z]+://", url):
                # Our function doesn't explicitly add it, relies on requests
                pass  # Requests itself handles the scheme, assert original url was passed

            mock_head.assert_called_once_with(expected_url, allow_redirects=False, timeout=25)
        else:
            mock_head.assert_not_called()


# --- Test Cases for Empty URL Exception ---
empty_url_cases = [
    (None, False, True),
    ("", False, True),
]


@pytest.mark.parametrize("url, allow_relative, allow_hash", empty_url_cases)
def test_empty_url_raises_exception(url, allow_relative, allow_hash):
    """Test test_url raises an exception for None or empty string URLs."""
    with pytest.raises(Exception, match="Empty url"):
        validate_url(url, allow_relative=allow_relative, allow_hash=allow_hash)


# --- Test Cases for Disallowed Hash Exception ---
disallowed_hash_cases = [
    ("#fragment-only", False, False),
    ("#another", True, False),
]


@pytest.mark.parametrize("url, allow_relative, allow_hash", disallowed_hash_cases)
def test_disallowed_hash_raises_exception(url, allow_relative, allow_hash):
    """Test test_url raises an exception for hash URLs when allow_hash=False."""
    with pytest.raises(Exception, match="Not allowed hash url"):
        validate_url(url, allow_relative=allow_relative, allow_hash=allow_hash)


# --- Test Cases for Disallowed Relative Exception ---
# Note: The relative path check in utils.py needs to be correct for these
disallowed_relative_cases = [
    ("/relative/path", False, True),
    ("../another/relative", False, False),
    ("./current/dir", False, True),
]


@pytest.mark.parametrize("url, allow_relative, allow_hash", disallowed_relative_cases)
def test_disallowed_relative_raises_exception(url, allow_relative, allow_hash):
    """Test test_url raises an exception for relative URLs when allow_relative=False."""
    with pytest.raises(Exception, match="Not allowed relative url"):
        validate_url(url, allow_relative=allow_relative, allow_hash=allow_hash)


# --- Test Cases for Network Request Errors ---
network_error_cases = [
    # ID, url, head_mock_config, expected_message_match
    ("http_notfound", "http://notfound.com", 404, "Invalid URL with code 404"),
    ("http_timeout", "http://timeout.com", requests.exceptions.Timeout, "Timeout connecting to URL"),
    ("http_connerror", "http://connerror.com", requests.exceptions.ConnectionError, "Connection error for URL"),
    (
        "http_reqerror",
        "http://reqerror.com",
        requests.exceptions.RequestException("detail"),
        "Error connecting to URL.*?detail",
    ),
    # Added case for missing schema
    ("missing_schema", "noscheme.com", requests.exceptions.MissingSchema, "Invalid URL format \(Missing Schema\?\).*?"),
    ("simple_string", "valid-url", requests.exceptions.MissingSchema, "Invalid URL format \(Missing Schema\?\).*?"),
]


@pytest.mark.parametrize(
    "case_id, url, head_mock_config, expected_message_match",
    network_error_cases,
    ids=[c[0] for c in network_error_cases],
)
def test_network_errors_raise_exception(monkeypatch, case_id, url, head_mock_config, expected_message_match):
    """Test test_url raises correct exceptions for network/format errors."""
    mock_head = None
    if isinstance(head_mock_config, int):  # Simulate a status code
        mock_response = MagicMock()
        mock_response.status_code = head_mock_config
        mock_head = MagicMock(return_value=mock_response)
    elif isinstance(head_mock_config, Exception):
        mock_head = MagicMock(side_effect=head_mock_config)
    elif issubclass(head_mock_config, Exception):
        # If it's a MissingSchema error, mock side effect directly
        if head_mock_config == requests.exceptions.MissingSchema:
            mock_head = MagicMock(side_effect=requests.exceptions.MissingSchema("Mocked missing schema"))
        else:
            mock_head = MagicMock(side_effect=head_mock_config("Mocked exception"))
    else:
        pytest.fail(f"Invalid head_mock_config type: {type(head_mock_config)}")

    monkeypatch.setattr(requests, "head", mock_head)

    with pytest.raises(Exception, match=expected_message_match):
        validate_url(url, allow_relative=False, allow_hash=True)

    # Only assert head was called if it's not a missing schema error
    # because missing schema happens before the call in requests
    if head_mock_config != requests.exceptions.MissingSchema:
        mock_head.assert_called_once_with(url, allow_redirects=False, timeout=25)
