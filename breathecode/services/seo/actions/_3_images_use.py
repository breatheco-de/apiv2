import logging
from urllib.parse import urlparse
from django.contrib.auth.models import User
from django.utils import timezone
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# You must always return a score number between 1 and 100
def images_use(client, report):

    asset = client.asset

    readme = asset.get_readme(parse=True)
    if 'html' not in readme:
        logger.fatal(f'Asset with {asset_slug} readme cannot be parse into an HTML')
        return False

    images = BeautifulSoup(readme['html'], features='html.parser').find_all('img')

    for image in images:
        if 'alt' not in image.attrs or image.attrs['alt'] == '':
            report.bad(-10, f'No alt found for image with source "{image.attrs["src"]}"')

    #report.good('No errors found on keyword density')


images_use.description = """
Include an alt message on each image.
"""
