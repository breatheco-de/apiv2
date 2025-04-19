import pytest

from breathecode.registry.utils import get_urls_from_html

# Parameters: (html_content, expected_urls, compare_as_set)
html_test_cases = [
    # No URLs
    ("<p>Some text without links or images.</p><div>Content</div>", [], False),
    # Only Anchors
    (
        """
        <p>Check <a href="https://example.com">this link</a>.</p>
        <a href="/relative/path">Relative</a>
        <a href="#fragment">Fragment</a>
        <a>No href</a>
    """,
        ["https://example.com", "/relative/path", "#fragment", None],
        False,
    ),
    # Only Images
    (
        """
        <img src="https://example.com/image.jpg">
        <img src="../images/local.png">
        <img>
    """,
        ["https://example.com/image.jpg", "../images/local.png", None],
        False,
    ),
    # Mixed Content (Order might vary, use set comparison)
    (
        """
        <h1>Title</h1>
        <p>Link: <a href="http://test.dev">Test</a></p>
        <img src="/logo.svg">
        <a href="https://another.link/page?q=1">Another</a>
        <img src="absolute/image.gif">
    """,
        ["http://test.dev", "https://another.link/page?q=1", "/logo.svg", "absolute/image.gif"],
        True,
    ),
    # Empty Input
    ("", [], False),
    # Malformed HTML (Order might vary, use set comparison)
    ('<a href="malformed.link" /> <img src="image.png" />', ["malformed.link", "image.png"], True),
]


@pytest.mark.parametrize("html_content, expected_urls, compare_as_set", html_test_cases)
def test_get_urls_from_html(html_content, expected_urls, compare_as_set):
    """Test get_urls_from_html with various HTML inputs."""
    result = get_urls_from_html(html_content)

    if compare_as_set:
        assert set(result) == set(expected_urls)
    else:
        assert result == expected_urls
