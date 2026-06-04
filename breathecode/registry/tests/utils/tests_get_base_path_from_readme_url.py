import pytest

from breathecode.registry.utils import get_base_path_from_readme_url


def test_get_base_path_from_readme_url_root():
    """README at repo root returns empty base_path."""
    url = "https://github.com/org/repo/blob/main/README.md"
    assert get_base_path_from_readme_url(url) == ""


def test_get_base_path_from_readme_url_subdirectory():
    """README in subdirectory returns that subdirectory as base_path."""
    url = "https://github.com/org/repo/blob/main/projects/myproject/README.md"
    assert get_base_path_from_readme_url(url) == "projects/myproject"


def test_get_base_path_from_readme_url_nested_subdirectory():
    """Nested path returns full dirname."""
    url = "https://github.com/org/repo/blob/master/foo/bar/baz/README.md"
    assert get_base_path_from_readme_url(url) == "foo/bar/baz"


def test_get_base_path_from_readme_url_empty_or_none():
    """None or empty URL returns empty string."""
    assert get_base_path_from_readme_url(None) == ""
    assert get_base_path_from_readme_url("") == ""


def test_get_base_path_from_readme_url_no_blob_path():
    """URL without blob/path returns empty string."""
    url = "https://github.com/org/repo"
    assert get_base_path_from_readme_url(url) == ""
