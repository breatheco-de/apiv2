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
