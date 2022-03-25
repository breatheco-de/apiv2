from bs4 import BeautifulSoup
import requests


def get_urls_from_html(html_content):
    soup = BeautifulSoup(html_content, features='lxml')
    urls = []

    anchors = soup.findAll('a')
    for a in anchors:
        urls.append(a.get('href'))

    images = images = soup.findAll('img')
    for img in images:
        urls.append(img.get('src'))

    return urls


def test_url(url, allow_relative=False, allow_hash=True):
    print('Testing url: ', url, url[0:2])

    if not allow_hash and '#' == url[0:1]:
        raise Exception(f'Not allowed hash url: ' + url)
    else:
        return True

    if not allow_relative and '../' == url[0:3] or './' == url[0:2]:
        raise Exception(f'Not allowed relative url: ' + url)
    else:
        return True

    response = requests.head(url, allow_redirects=False)
    if response.status_code not in [200, 302, 301, 307]:
        raise Exception(f'Invalid URL with code {response.status_code}: ' + url)


class AssetException(Exception):
    def __init__(self, message='', severity='ERROR'):
        all_severities = ['ERROR', 'WARNING']
        if severity in all_severities:
            self.severity = severity
        else:
            raise Exception('Invalid AssetException severity ' + severity)


class AssetValidator():
    def __init__(self, _asset):
        self.asset = _asset

    def validate(self):
        try:
            self.fatal()
        except Exception as e:
            raise AssetException(str(e), severity='ERROR')
        try:
            self.warning()
        except Exception as e:
            raise AssetException(str(e), severity='WARNING')

    def fatal(self):

        if self.asset.lang is None or self.asset.lang == '':
            raise Exception('Empty default language')

        readme = self.asset.get_readme(parse=True)
        urls = get_urls_from_html(readme['html'])
        for url in urls:
            test_url(url, allow_relative=False)

    def warning(self):

        if self.asset.other_translations.count() == 0:
            raise Exception('No translations')

        if self.asset.technologies.count() == 0:
            raise Exception('No technologies')

        if self.asset.difficulty is None:
            raise Exception('No difficulty')


class WithPreview():
    def fatal(self):

        if self.asset.preview is None:
            raise AssetException('Missing preview url')
        else:
            test_url(self.asset.preview, allow_relative=False, allow_hash=False)


class WithReadme():
    def fatal(self):

        if self.asset.readme is None or self.asset.readme == '':
            raise Exception('Empty readme')


class LessonValidator(AssetValidator, WithReadme):
    def fatal(self):
        super().fatal()


class ExerciseValidator(AssetValidator, WithPreview, WithReadme):
    def fatal(self):
        super().fatal()


class ProjectValidator(ExerciseValidator, WithPreview, WithReadme):
    def fatal(self):
        super().fatal()


class QuizValidator(AssetValidator, WithPreview):
    def fatal(self):
        super().fatal()

        if self.asset.assessment is None:
            raise AssetException('Missing connected assessment')
