import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# You must always return a score number between 1 and 100
def keyword_density(client, report):

    def remove_three_characters_words(str):
        words = str.split(" ")
        words = list(filter(lambda word: len(word) > 3, words))
        return " ".join(words)

    asset = client.asset

    readme = asset.get_readme(parse=True)
    if "html" not in readme:
        report.fatal(f"Asset with {asset.slug} readme cannot be parse into an HTML")
        return False

    all_h2s = []
    h2s = BeautifulSoup(readme["html"], features="html.parser").find_all("h2")
    for h in h2s:
        all_h2s.append(h.contents[0])

    for keyword in asset.seo_keywords.all():
        h2s_with_keywords = []
        cleaned_title = remove_three_characters_words(keyword.title)
        for h2 in all_h2s:
            if cleaned_title.lower() in remove_three_characters_words(h2).lower():
                h2s_with_keywords.append(h2)

        if len(h2s_with_keywords) > 2:
            report.bad(
                -20,
                f'Too many h2 tags contain the target keyword "{keyword.title}", please consider a max of 2 h2 tags with the keyword',
            )
        elif len(h2s_with_keywords) == 0:
            report.bad(-20, f'Please add the target keyword "{keyword.title}" to at least one tag')


keyword_density.description = """
Include the keyword in the H1 and one of the H2s.
Use the keyword between 2 or 3 times during the article.
"""
