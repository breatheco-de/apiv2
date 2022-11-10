import logging
from urllib.parse import urlparse
from django.contrib.auth.models import User
from django.utils import timezone
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# You must always return a score number between 1 and 100
def internal_linking(client, report):

    asset = client.asset

    missing_cluster_paths = []
    main_domain = ''
    for keyword in asset.seo_keywords.all():
        if keyword.cluster is not None:
            if keyword.cluster.landing_page_url is None or keyword.cluster.landing_page_url == '':
                report.fatal(f'Cluster {keyword.cluster.slug} its missing a landing page url')
                continue

            url = urlparse(keyword.cluster.landing_page_url).path
            if url.netloc != '': main_domain = url.netloc
            if url == '': url = keyword.cluster.landing_page_url
            missing_cluster_paths.append(url)

    if len(missing_cluster_paths) == 0:
        report.fatal('No valid clusters landing urls')

    readme = asset.get_readme(parse=True)
    if 'html' not in readme:
        logger.fatal(f'Asset with {asset_slug} readme cannot be parse into an HTML')
        return False

    links = BeautifulSoup(readme['html'], features='html.parser').find_all('a')
    found_links_to_clusters = []
    internal_links = []
    for link in links:
        if 'href' not in link.attrs:
            report.bad(-1, f'No href found for anchor with label "{link.contents[0]}"')

        href = link.attrs['href']
        url = urlparse(href)

        # clusters must be linked
        if url.netloc == main_domain:
            internal_links.append(href)

        # clusters must be linked
        path = url.path
        if path == '': path = href
        missing_cluster_paths = [i for i in missing_cluster_paths if i != path]

    for path in missing_cluster_paths:
        report.fatal(f'Missing link to cluster: {path}')

    total_internal = len(internal_links)
    if total_internal < 4:
        missing = 4 - total_internal
        report.bad(-(missing * 5), f'Please add at least {missing} more internal links')

    #report.good('No errors found on keyword density')


internal_linking.description = """
Include a link to all the keyword clusters associated with the asset.
Include at least 3 links to other internal pages.
"""
