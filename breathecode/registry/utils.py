import logging

import requests
from bs4 import BeautifulSoup

from breathecode.authenticate.models import CredentialsGithub
from breathecode.services.github import Github, GithubAuthException

logger = logging.getLogger(__name__)


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


def test_url(url, allow_relative=False, allow_hash=True):
    if url is None or url == "":
        raise Exception("Empty url")

    if not allow_hash and "#" == url[0:1]:
        raise Exception("Not allowed hash url: " + url)

    if not allow_relative and ("../" == url[0:3] or "./" == url[0:2]):
        raise Exception("Not allowed relative url: " + url)

    return True

    # FIXME: the code is under this line is unaccessible, want you remove it?
    # response = requests.head(url, allow_redirects=False, timeout=2)
    # if response.status_code not in [200, 302, 301, 307]:
    #     raise Exception(f'Invalid URL with code {response.status_code}: ' + url)


class AssetException(Exception):

    def __init__(self, message="", severity="ERROR"):
        all_severities = ["ERROR", "WARNING"]
        if severity in all_severities:
            self.severity = severity
        else:
            raise Exception("Invalid AssetException severity " + severity)


class AssetValidator:
    base_warns = ["translations", "technologies"]
    base_errors = ["lang", "urls", "category", "preview", "images", "readme_url"]
    warns = []
    errors = []

    def __init__(self, _asset):
        self.asset = _asset
        self.warns = self.base_warns + self.warns
        self.errors = self.base_errors + self.errors

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
                    print("validating warning " + validation)
                    getattr(self, validation)()
                else:
                    raise Exception("Invalid asset warning validation " + validation)
        except Exception as e:
            raise AssetException(str(e), severity="WARNING")

    def readme_url(self):
        if self.asset.readme_url is not None or self.asset.readme_url != "":
            if not self.asset.owner:
                raise Exception("Asset must have an owner and the owner must have write access to the readme file")

            credentials = CredentialsGithub.objects.filter(user=self.asset.owner).first()
            if credentials is None:
                raise Exception("Github credentials for asset owner were not found")

            gb = Github(credentials.token)
            try:
                if not gb.file_exists(self.asset.readme_url):
                    raise AssetException("Readme URL points to a missing file", severity="ERROR")
            except GithubAuthException:
                raise AssetException(
                    "Cannot connect to github to validate readme url, please fix owner or credentials", severity="ERROR"
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
            raise Exception("Empty default language")

    def translations(self):
        if self.asset.all_translations.count() == 0:
            raise Exception("No translations")

    def technologies(self):
        if self.asset.technologies.count() == 0:
            raise Exception("No technologies")

    def difficulty(self):
        if self.asset.difficulty is None:
            raise Exception("No difficulty")

    def preview(self):
        pass
        # TODO: Comment this out for now, we will uncomment when preview url generates automatically
        # if self.asset.preview is None:
        #     raise Exception('Missing preview url')
        # else:
        #     test_url(self.asset.preview, allow_relative=False, allow_hash=False)

    def readme(self):
        if self.asset.readme is None or self.asset.readme == "" and not self.asset.external:
            raise Exception("Empty readme")

    def category(self):

        if self.asset.category is None:
            raise Exception("Empty category")

    def images(self):
        images = self.asset.images.all()
        print("Validating images", images)
        for image in images:
            if image.download_status != "OK":
                raise Exception("Check the asset images, there seems to be images not properly downloaded")


class LessonValidator(AssetValidator):
    warns = []
    errors = ["readme"]


class ArticleValidator(AssetValidator):
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
