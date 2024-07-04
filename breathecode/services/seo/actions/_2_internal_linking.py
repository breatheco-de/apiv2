import logging, re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# You must always return a score number between 1 and 100
def internal_linking(client, report):

    asset = client.asset

    missing_cluster_paths = []
    main_domain = ""
    for keyword in asset.seo_keywords.all():
        if keyword.cluster is not None:
            if keyword.cluster.landing_page_url is None or keyword.cluster.landing_page_url == "":
                report.fatal(f"Cluster {keyword.cluster.slug} its missing a landing page url")
                continue

            url = urlparse(keyword.cluster.landing_page_url)
            if url.netloc != "":
                main_domain = url.netloc
            if url.path == "":
                url = keyword.cluster.landing_page_url
            missing_cluster_paths.append(url.path)

    if len(missing_cluster_paths) == 0:
        report.fatal("No valid clusters landing urls")

    readme = asset.get_readme(parse=True)
    if "html" not in readme:
        logger.fatal(f"Asset with {asset.slug} readme cannot be parse into an HTML")
        return False

    links = BeautifulSoup(readme["html"], features="html.parser").find_all("a")

    internal_links = []
    for link in links:
        if "href" not in link.attrs:
            report.bad(-1, f'No href found for anchor with label "{link.contents[0]}"')

        href = link.attrs["href"]
        url = urlparse(href)

        # clusters must be linked
        if url.netloc == main_domain:
            internal_links.append(href)

        # clusters must be linked
        path = url.path
        if path == "":
            path = href
        missing_cluster_paths = [i for i in missing_cluster_paths if i.lower() != path.lower()]

    for path in missing_cluster_paths:
        report.fatal(f"Missing link to cluster: {path}")

    total_internal = len(internal_links)
    if total_internal < 4:
        missing = 4 - total_internal
        report.bad(-(missing * 5), f"Please add at least {missing} more internal links")

    missing_links = False
    text = readme["decoded"]
    url_regex = re.compile(r"[^!]\[.*\]\(.*\)")

    words = text.split()
    words = [" ".join(words[i : i + 500]) for i in range(0, len(words), 500)]

    for word in words:
        urls = re.findall(url_regex, word)
        if len(urls) == 0:
            missing_links = True
            break

    if missing_links:
        report.bad(-15, "Please add at least a link every 500 words")

    # report.good('No errors found on keyword density')


internal_linking.description = """
Include a link to all the keyword clusters associated with the asset.
Include at least 3 links to other internal pages.
Include at least one link every 500 words.
"""
