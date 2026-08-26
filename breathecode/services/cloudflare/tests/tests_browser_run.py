from unittest.mock import MagicMock, patch

import pytest
import requests

from breathecode.services.cloudflare.browser_run import BrowserRun, ScreenshotResponse


@pytest.fixture
def cf_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "test-account")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "test-token")


def test_screenshot__missing_config(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)

    response = BrowserRun().screenshot("https://example.com")

    assert isinstance(response, ScreenshotResponse)
    assert response.status_code == 500
    assert response.content == b""


def test_screenshot__success(cf_env):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"png-bytes"
    mock_response.headers = {"content-type": "image/png"}

    with patch("breathecode.services.cloudflare.browser_run.requests.post", return_value=mock_response) as post:
        response = BrowserRun().screenshot("https://example.com", "1200x630", delay=1000)

    assert response.status_code == 200
    assert response.content == b"png-bytes"
    post.assert_called_once()
    args, kwargs = post.call_args
    assert args[0] == (
        "https://api.cloudflare.com/client/v4/accounts/test-account/browser-rendering/screenshot"
    )
    assert kwargs["json"]["url"] == "https://example.com"
    assert kwargs["json"]["viewport"] == {"width": 1200, "height": 630}
    assert kwargs["json"]["waitForTimeout"] == 1000
    assert kwargs["headers"]["Authorization"] == "Bearer test-token"
    assert kwargs["timeout"] == 90


def test_screenshot__http_error(cf_env):
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.content = b"bad request"
    mock_response.headers = {"content-type": "application/json"}

    with patch("breathecode.services.cloudflare.browser_run.requests.post", return_value=mock_response):
        response = BrowserRun().screenshot("https://example.com")

    assert response.status_code == 400


def test_screenshot__request_exception(cf_env):
    with patch(
        "breathecode.services.cloudflare.browser_run.requests.post",
        side_effect=requests.exceptions.Timeout("timed out"),
    ):
        response = BrowserRun().screenshot("https://example.com")

    assert response.status_code == 500
    assert response.content == b""


@pytest.mark.asyncio
async def test_ascreenshot__success(cf_env):
    class FakeResponse:
        status = 200
        headers = {"content-type": "image/png"}

        async def read(self):
            return b"png-bytes"

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeSession:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            return FakeResponse()

    with patch("breathecode.services.cloudflare.browser_run.aiohttp.ClientSession", FakeSession):
        response = await BrowserRun().ascreenshot("https://example.com", "1024x707", delay=3000)

    assert response.status_code == 200
    assert response.content == b"png-bytes"
    assert response.headers["content-type"] == "image/png"
