import logging
import os

import aiohttp
import requests

logger = logging.getLogger(__name__)

__all__ = ["BrowserRun", "ScreenshotResponse"]

SCREENSHOT_HTTP_TIMEOUT = 90
DEFAULT_DIMENSION = "1200x630"


class ScreenshotResponse:
    """Minimal response shape used by generate_screenshot callers."""

    def __init__(self, content=b"", status_code=500, headers=None):
        self.content = content or b""
        self.status_code = status_code
        self.status = status_code
        self.headers = headers or {"content-type": "image/png"}


class BrowserRun:
    """Cloudflare Browser Run (Browser Rendering) screenshot client."""

    def __init__(self):
        self.account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
        self.api_token = os.getenv("CLOUDFLARE_API_TOKEN", "")

    def screenshot_url(self) -> str:
        return (
            f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/browser-rendering/screenshot"
        )

    def _safe_url(self, url: str) -> str:
        if "?" in url:
            return url.split("?")[0] + "?***"
        return url

    def _parse_dimension(self, dimension: str) -> tuple[int, int]:
        try:
            width_str, height_str = dimension.lower().split("x")
            return int(width_str), int(height_str)
        except (ValueError, AttributeError):
            width_str, height_str = DEFAULT_DIMENSION.split("x")
            return int(width_str), int(height_str)

    def build_payload(self, url: str, dimension: str = DEFAULT_DIMENSION, **kwargs) -> dict:
        width, height = self._parse_dimension(dimension)
        delay = kwargs.get("delay", 1000)
        try:
            delay = int(delay)
        except (TypeError, ValueError):
            delay = 1000

        payload = {
            "url": url,
            "viewport": {"width": width, "height": height},
            "gotoOptions": {
                "waitUntil": "networkidle0",
                "timeout": 60000,
            },
            "screenshotOptions": {
                "type": "png",
                "fullPage": False,
            },
            "waitForTimeout": delay,
        }

        user_agent = kwargs.get("user-agent") or kwargs.get("userAgent")
        if user_agent:
            payload["userAgent"] = user_agent

        return payload

    def _missing_config_response(self) -> ScreenshotResponse:
        logger.error("CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_API_TOKEN is not configured")
        return ScreenshotResponse(b"", 500)

    def screenshot(self, url: str, dimension: str = DEFAULT_DIMENSION, **kwargs):
        logger.info("Generating screenshot url=%s dimension=%s", self._safe_url(url), dimension)

        if not self.account_id or not self.api_token:
            return self._missing_config_response()

        payload = self.build_payload(url, dimension, **kwargs)
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                self.screenshot_url(),
                json=payload,
                headers=headers,
                timeout=SCREENSHOT_HTTP_TIMEOUT,
            )
        except requests.exceptions.RequestException as e:
            logger.error("Error calling Cloudflare Browser Run: %s", str(e))
            return ScreenshotResponse(b"", 500)

        content_len = len(response.content or b"")
        logger.info("Screenshot response status=%s bytes=%s", response.status_code, content_len)
        if response.status_code != 200:
            logger.error("Cloudflare Browser Run returned status=%s", response.status_code)

        return response

    async def ascreenshot(self, url: str, dimension: str = DEFAULT_DIMENSION, **kwargs) -> ScreenshotResponse:
        logger.info("Generating screenshot url=%s dimension=%s", self._safe_url(url), dimension)

        if not self.account_id or not self.api_token:
            return self._missing_config_response()

        payload = self.build_payload(url, dimension, **kwargs)
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        try:
            timeout = aiohttp.ClientTimeout(total=SCREENSHOT_HTTP_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.screenshot_url(), json=payload, headers=headers) as response:
                    content = await response.read()
                    content_type = response.headers.get("content-type", "image/png")
                    logger.info("Screenshot response status=%s bytes=%s", response.status, len(content))
                    if response.status != 200:
                        logger.error("Cloudflare Browser Run returned status=%s", response.status)
                    return ScreenshotResponse(content, response.status, {"content-type": content_type})
        except Exception as e:
            logger.error("Error calling Cloudflare Browser Run: %s", str(e))
            return ScreenshotResponse(b"", 500)
