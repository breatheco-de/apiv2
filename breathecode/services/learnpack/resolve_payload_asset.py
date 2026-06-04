"""Resolve a single Asset / asset id from LearnPack payload ``asset_id`` (scalar or comma-separated)."""

from __future__ import annotations

from typing import TYPE_CHECKING

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
