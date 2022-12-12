import logging
from django.contrib.auth.models import User
from django.utils import timezone
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# You must always return a score number between 1 and 100
def keyword_density(client, report):

    asset = client.asset

    readme = asset.get_readme(parse=True)
    if 'html' not in readme:
        report.fatal(f'Asset with {asset_slug} readme cannot be parse into an HTML')
        return False

    all_h2s = []
    h2s = BeautifulSoup(readme['html'], features='html.parser').find_all('h2')
    for h in h2s:
        all_h2s.append(h.contents[0])

    for keyword in asset.seo_keywords.all():
        h2s_with_keywords = []
        for h2 in all_h2s:
            if keyword.title in h2:
                h2s_with_keywords.append(h2)

        if len(h2s_with_keywords) > 2:
            report.bad(
                -20,
                f'Too many h2 tags contain the target keyword "{keyword.title}", please consider a max of 2 h2 tags'
            )
        elif len(h2s_with_keywords) == 0:
            report.bad(-20, f'Please add the target keyword "{keyword.title}" to at least one tag')


keyword_density.description = """
Include the keyword in the H1 and one of the H2s.
Use the keyword between 2 or 3 times during the article.
"""
