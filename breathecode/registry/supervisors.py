import logging
from datetime import timedelta

from django.db.models import Count, Q

from breathecode.registry.models import Asset
from breathecode.utils.decorators import supervisor

logger = logging.getLogger(__name__)


@supervisor(delta=timedelta(hours=1))
def check_asset_integrity(**kwargs):
    """
    Supervisor to check for assets with missing primary technology or short descriptions.
    """
    logger.debug("Starting check_asset_integrity supervisor")

    # Assets without a technology with sort_priority=1
    assets_missing_primary_tech = Asset.objects.annotate(
        primary_tech_count=Count("technologies", filter=Q(technologies__sort_priority=1))
    ).filter(primary_tech_count=0, status="PUBLISHED", visibility="PUBLIC")

    for asset in assets_missing_primary_tech:
        message = f"Asset {asset.slug} (ID: {asset.id}) has no technology with sort_priority=1."
        code = "asset-missing-primary-technology"
        params = {"asset_id": asset.id}
        yield message, code, params
        logger.info(f"Found asset {asset.slug} (ID: {asset.id}) missing primary technology.")

    # Assets with description null or shorter than 80 characters
    assets_short_description_query = Asset.objects.filter(
        Q(description__isnull=True) | Q(description__lt=80), status="PUBLISHED", visibility="PUBLIC"
    )

    for asset in assets_short_description_query:
        # Avoid duplicating issues if already caught by the first check
        if asset not in list(assets_missing_primary_tech):
            message = f"Asset {asset.slug} (ID: {asset.id}) has a description shorter than 80 characters or null."
            code = "asset-short-description"
            params = {"asset_id": asset.id}
            yield message, code, params
            logger.info(f"Found asset {asset.slug} (ID: {asset.id}) with short/missing description.")

    logger.debug("Finished check_asset_integrity supervisor")
