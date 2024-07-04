import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# You must always return a score number between 1 and 100
def general_structure(client, report):

    asset = client.asset

    readme = asset.get_readme(parse=True)
    if "html" not in readme:
        report.fatal(f"Asset with {asset.slug} readme cannot be parse into an HTML")
        return False

    h1s = BeautifulSoup(readme["html"], features="html.parser").find_all("h1")
    total_h1s = len(h1s)
    if total_h1s > 0:
        report.bad(-20, f"We found {total_h1s} please remove all of them")

    h2s = BeautifulSoup(readme["html"], features="html.parser").find_all("h2")
    if len(h2s) == 0:
        report.bad(-20, "Include at least one h2 heading in the article")


general_structure.description = """
Do not include h1 because its already included as the article title.
Include at least 1 h2.
At least 600 words.
"""
