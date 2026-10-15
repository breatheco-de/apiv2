"""Resolve a single Asset / asset id from LearnPack payload ``asset_id`` (scalar or comma-separated)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from breathecode.utils.validators.language import languages_equivalent

if TYPE_CHECKING:
    from breathecode.registry.models import Asset


def parse_asset_id_candidates(raw) -> list[int]:
    """Split comma-separated ids; strip; skip invalid segments. ``bool`` is ignored (subtype of int)."""
    if raw is None:
        return []
    if isinstance(raw, bool):
        return []
    if isinstance(raw, int):
        return [raw]
    s = str(raw).strip()
    if not s:
        return []
    out: list[int] = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except ValueError:
            continue
    return out


def get_asset_id_raw_from_learnpack_payload(payload: dict | None) -> Any:
    """
    Prefer root ``asset_id`` / ``asset_ids``, then nested ``payload.package`` or ``package``.

    JSON arrays are normalized to a comma-separated string so ``parse_asset_id_candidates``
    can keep its original scalar/CSV contract.
    """
    if not payload or not isinstance(payload, dict):
        return None

    raw = None
    for key in ("asset_id", "asset_ids"):
        if key in payload and payload[key] is not None:
            raw = payload[key]
            break

    if raw is None:
        for package_container in (payload.get("payload"), payload):
            if not isinstance(package_container, dict):
                continue
            package = package_container.get("package")
            if not isinstance(package, dict):
                continue
            for key in ("asset_id", "asset_ids"):
                if key in package and package[key] is not None:
                    raw = package[key]
                    break
            if raw is not None:
                break

    if isinstance(raw, list):
        return ",".join(str(item) for item in raw)

    return raw


def _select_asset_for_candidate_ids(candidate_ids: list[int]) -> Asset | None:
    from breathecode.registry.models import Asset

    if not candidate_ids:
        return None
    assets = list(Asset.objects.filter(id__in=candidate_ids))
    if not assets:
        return None
    english = [a for a in assets if languages_equivalent(a.lang, "en")]
    pool = english if english else assets
    return min(pool, key=lambda a: a.id)


def resolve_asset_id_from_candidates(candidate_ids: list[int]) -> int | None:
    asset = _select_asset_for_candidate_ids(candidate_ids)
    return asset.id if asset else None


def resolve_asset_id_from_payload_value(raw) -> int | None:
    return resolve_asset_id_from_candidates(parse_asset_id_candidates(raw))


def resolve_asset_from_payload_asset_id(raw) -> Asset | None:
    return _select_asset_for_candidate_ids(parse_asset_id_candidates(raw))


def translation_slugs_for_asset(asset: Asset) -> set[str]:
    """Slugs of this asset plus its canonical translation group."""
    canonical = asset.get_canonical_translation_asset()
    slugs = {canonical.slug, asset.slug}
    slugs.update(elem.slug for elem in canonical.all_translations.all() if elem and elem.slug)
    return {slug for slug in slugs if slug}


def collect_learnpack_candidate_assets(payload: dict | None) -> list[Asset]:
    """
    All registry assets that may belong to this LearnPack event.

    LearnPack can send several asset ids for one package (translations + duplicates).
    We keep every candidate and also pull siblings that share ``learnpack_id``.
    """
    from breathecode.registry.models import Asset

    if not payload or not isinstance(payload, dict):
        return []

    raw = get_asset_id_raw_from_learnpack_payload(payload)
    ids = parse_asset_id_candidates(raw)
    by_id: dict[int, Asset] = {}
    if ids:
        for asset in Asset.objects.filter(id__in=ids):
            by_id[asset.id] = asset

    slug = payload.get("slug") or payload.get("package_slug")
    if slug:
        by_slug = Asset.get_by_slug(slug)
        if by_slug is not None:
            by_id[by_slug.id] = by_slug

    learnpack_ids: set[int] = {asset.learnpack_id for asset in by_id.values() if asset.learnpack_id}
    if "package_id" in payload:
        try:
            learnpack_ids.add(int(payload["package_id"]))
        except (TypeError, ValueError):
            pass

    if learnpack_ids:
        for asset in Asset.objects.filter(learnpack_id__in=learnpack_ids):
            by_id[asset.id] = asset

    return list(by_id.values())
