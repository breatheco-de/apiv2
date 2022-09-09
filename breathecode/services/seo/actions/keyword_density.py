import logging
from django.contrib.auth.models import User
from django.utils import timezone

logger = logging.getLogger(__name__)


# You must always return a score number between 1 and 100
def keyword_density(client, report):

    asset = client.asset

    if asset.seo_keywords is None or asset.seo_keywords.count() == 0:
        report.fatal('Asset has not keywords associated')

    if asset.readme is None:
        report.fatal('Asset not content')
        
    report.good('No errors found on keyword density')
