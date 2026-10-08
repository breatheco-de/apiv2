from __future__ import annotations

from django.core.cache import cache

from breathecode.admissions.actions import ASSET_LIST_KEYS, _resolve_slug_to_asset_id, is_deleted_marker
from breathecode.admissions.models import SyllabusVersion
from breathecode.admissions.services.completion import _load_syllabus_json

SYLLABUS_SKILLS_CACHE_TTL_SECONDS = 60 * 60 * 24
DIFFICULTY_ORDER = {"BEGINNER": 0, "EASY": 1, "INTERMEDIATE": 2, "HARD": 3}


def _collect_syllabus_assets(syllabus_json: dict) -> dict[str, dict]:
    """Return {asset_slug: {"days": set[int], "mandatory": bool}} for every asset referenced in the syllabus."""

    assets: dict[str, dict] = {}

    for index, day in enumerate(syllabus_json.get("days", [])):
        if not isinstance(day, dict):
            continue

        position = day.get("position") or index + 1

        for key in ASSET_LIST_KEYS:
            items = day.get(key)
            if not isinstance(items, list):
                continue

            for item in items:
                if not isinstance(item, dict) or not item or is_deleted_marker(item):
                    continue

                slug = item.get("slug")
                if not isinstance(slug, str) or not slug:
                    continue

                info = assets.setdefault(slug, {"days": set(), "mandatory": False})
                info["days"].add(position)
                info["mandatory"] = info["mandatory"] or item.get("mandatory", True) is not False

    return assets


def _harder(current: str | None, candidate: str | None) -> str | None:
    if candidate not in DIFFICULTY_ORDER:
        return current

    if current is None or DIFFICULTY_ORDER[candidate] > DIFFICULTY_ORDER[current]:
        return candidate

    return current


def compute_syllabus_skills(syllabus_version: SyllabusVersion) -> dict:
    """Union of the skills of every asset referenced in the syllabus version."""

    from breathecode.registry.models import AssetSkill

    assets_by_slug = _collect_syllabus_assets(_load_syllabus_json(syllabus_version))
    slug_to_id = _resolve_slug_to_asset_id(set(assets_by_slug))

    # two slugs (e.g. an alias and the current slug) can point to the same asset
    assets_by_id: dict[int, dict] = {}
    for slug, info in assets_by_slug.items():
        asset_id = slug_to_id.get(slug)
        if asset_id is None:
            continue

        merged = assets_by_id.setdefault(asset_id, {"days": set(), "mandatory": False})
        merged["days"] |= info["days"]
        merged["mandatory"] = merged["mandatory"] or info["mandatory"]

    rows = AssetSkill.objects.filter(asset_id__in=assets_by_id.keys()).values(
        "asset_id",
        "skill__slug",
        "skill__name",
        "skill__domain__slug",
        "asset__asset_type",
        "asset__difficulty",
    )

    skills: dict[str, dict] = {}
    mapped_asset_ids: set[int] = set()

    for row in rows:
        asset_info = assets_by_id[row["asset_id"]]
        mapped_asset_ids.add(row["asset_id"])

        skill = skills.setdefault(
            row["skill__slug"],
            {
                "slug": row["skill__slug"],
                "name": row["skill__name"],
                "domain": row["skill__domain__slug"],
                "asset_ids": set(),
                "by_asset_type": {},
                "max_difficulty": None,
                "days": set(),
                "mandatory": False,
            },
        )

        skill["asset_ids"].add(row["asset_id"])
        asset_type = row["asset__asset_type"]
        skill["by_asset_type"][asset_type] = skill["by_asset_type"].get(asset_type, 0) + 1
        skill["max_difficulty"] = _harder(skill["max_difficulty"], row["asset__difficulty"])
        skill["days"] |= asset_info["days"]
        skill["mandatory"] = skill["mandatory"] or asset_info["mandatory"]

    result = []
    for skill in skills.values():
        asset_ids = skill.pop("asset_ids")
        result.append(
            {
                **skill,
                "asset_count": len(asset_ids),
                "days": sorted(skill["days"]),
            }
        )

    result.sort(key=lambda x: (-x["asset_count"], x["slug"]))

    return {
        "syllabus": syllabus_version.syllabus.slug if syllabus_version.syllabus else None,
        "version": syllabus_version.version,
        "total_assets": len(assets_by_id),
        "unmapped_assets": len(assets_by_id) - len(mapped_asset_ids),
        "unresolved_slugs": sorted(slug for slug in assets_by_slug if slug not in slug_to_id),
        "skills": result,
    }


def get_syllabus_skills(syllabus_version: SyllabusVersion) -> dict:
    """
    Cached version of compute_syllabus_skills.

    The key changes when the syllabus version is saved (updated_at) or when the skills of any asset change
    (skills generation), so it never needs manual invalidation.
    """

    from breathecode.registry.actions import get_skills_generation

    key = f"syllabus-skills:{syllabus_version.id}:{syllabus_version.updated_at.timestamp()}:{get_skills_generation()}"
    result = cache.get(key)
    if result is None:
        result = compute_syllabus_skills(syllabus_version)
        cache.set(key, result, timeout=SYLLABUS_SKILLS_CACHE_TTL_SECONDS)

    return result
