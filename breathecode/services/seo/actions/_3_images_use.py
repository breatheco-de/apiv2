import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# You must always return a score number between 1 and 100
def images_use(client, report):

    asset = client.asset

    readme = asset.get_readme(parse=True)
    if "html" not in readme:
        logger.fatal(f"Asset with {asset.slug} readme cannot be parse into an HTML")
        return False

    images = BeautifulSoup(readme["html"], features="html.parser").find_all("img")

    for image in images:
        if "alt" not in image.attrs or image.attrs["alt"] == "":
            report.bad(-10, f'No alt found for image with source "{image.attrs["src"]}"')

    if len(images) == 0:
        report.bad(-5, "Article must have at least one image, diagram or graphic")

    # report.good('No errors found on keyword density')


images_use.description = """
Include an alt message on each image.
"""
