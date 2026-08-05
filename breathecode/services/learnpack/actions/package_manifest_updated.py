import logging

from breathecode.assignments.models import LearnPackWebhook

logger = logging.getLogger(__name__)


def package_manifest_updated(self, webhook: LearnPackWebhook):
    """
    Sync only the LearnPack Cloud manifest onto existing Asset(s).

    Same payload shape as ``package_published``, but does not touch learnpack_id,
    deploy URL, or learn.json config.
    """
    # lazyload to fix circular import
    from breathecode.registry.models import Asset
    from breathecode.services.learnpack.resolve_payload_asset import (
        get_asset_id_raw_from_learnpack_payload,
        parse_asset_id_candidates,
    )

    payload = webhook.payload or {}
    nested_payload = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    package = {}
    if isinstance(nested_payload.get("package"), dict):
        package = nested_payload["package"]
    elif isinstance(payload.get("package"), dict):
        package = payload["package"]

    assets = []
    candidate_ids = parse_asset_id_candidates(get_asset_id_raw_from_learnpack_payload(payload))
    if candidate_ids:
        assets = list(Asset.objects.filter(id__in=candidate_ids))

    if not assets:
        _slug = None
        if "slug" in payload:
            _slug = payload["slug"]
        elif "package_slug" in payload:
            _slug = payload["package_slug"]
        elif package.get("package_slug"):
            _slug = package["package_slug"]

        if _slug is not None:
            asset = Asset.get_by_slug(_slug)
            if asset is not None:
                assets = [asset]

    package_id = payload.get("package_id")
    if package_id is None:
        package_id = package.get("id")
    if package_id is not None:
        try:
            package_id = int(package_id)
        except (TypeError, ValueError):
            raise Exception(f"Invalid package_id in package_manifest_updated payload: {package_id}")

    if not assets and package_id is not None:
        asset = Asset.objects.filter(learnpack_id=package_id).first()
        if asset is not None:
            assets = [asset]

    if not assets:
        raise Exception(
            "Asset specified by learnpack package_manifest_updated was not found using either the payload 'asset_id' or 'slug'"
        )

    manifest = nested_payload.get("manifest")
    if not isinstance(manifest, dict):
        raise Exception("Impossible to retrieve learnpack manifest from package_manifest_updated payload")

    for asset in assets:
        if asset.manifest != manifest:
            asset.manifest = manifest
            asset.save(update_fields=["manifest"])
