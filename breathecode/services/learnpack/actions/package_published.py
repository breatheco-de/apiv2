import json
import logging

from breathecode.assignments.models import LearnPackWebhook

logger = logging.getLogger(__name__)


def package_published(self, webhook: LearnPackWebhook):
    """
    Sync LearnPack Cloud publication fields onto existing Asset(s).

    Updates learnpack_id (only if unset), learnpack_deploy_url, and learnpack manifest.
    If package.config changed vs asset.config, reapplies learn.json metadata
    via apply_learn_config.

    When ``asset_id`` / ``asset_ids`` contains multiple ids (CSV or list), all
    matching assets are updated. Ids may be at the payload root or under
    ``payload.package`` / ``package``.
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

    # Final fallback: try resolving by LearnPack package_id if available.
    package_id = payload.get("package_id")
    if package_id is None:
        package_id = package.get("id")
    if package_id is not None:
        try:
            package_id = int(package_id)
        except (TypeError, ValueError):
            raise Exception(f"Invalid package_id in package_published payload: {package_id}")

    if not assets and package_id is not None:
        asset = Asset.objects.filter(learnpack_id=package_id).first()
        if asset is not None:
            assets = [asset]

    if not assets:
        raise Exception(
            "Asset specified by learnpack package_published was not found using either the payload 'asset_id' or 'slug'"
        )

    deploy_url = package.get("custom_deployment_url") or package.get("deployment_url")

    learn_config = package.get("config")
    if isinstance(learn_config, str):
        try:
            learn_config = json.loads(learn_config) if learn_config.strip() else None
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid package.config JSON in package_published payload: {e}") from e
    if not isinstance(learn_config, dict):
        learn_config = None

    manifest = nested_payload.get("manifest")
    if not isinstance(manifest, dict):
        manifest = None

    for asset in assets:
        update_fields = []

        if package_id is not None and asset.learnpack_id is None:
            asset.learnpack_id = package_id
            update_fields.append("learnpack_id")

        if deploy_url is not None and deploy_url != "" and asset.learnpack_deploy_url != deploy_url:
            asset.learnpack_deploy_url = deploy_url
            update_fields.append("learnpack_deploy_url")

        if manifest is not None and asset.manifest != manifest:
            asset.manifest = manifest
            update_fields.append("manifest")

        if update_fields:
            asset.save(update_fields=update_fields)

        if learn_config is not None and asset.config != learn_config:
            asset.config = learn_config
            asset.apply_learn_config(learn_config)
