import capyc.pytest as capy

from breathecode.services.learnpack.resolve_payload_asset import (
    parse_asset_id_candidates,
    resolve_asset_from_payload_asset_id,
    resolve_asset_id_from_candidates,
    resolve_asset_id_from_payload_value,
)


def test_parse_asset_id_candidates_split_and_skips_invalid():
    assert parse_asset_id_candidates(None) == []
    assert parse_asset_id_candidates("") == []
    assert parse_asset_id_candidates("  ") == []
    assert parse_asset_id_candidates(True) == []
    assert parse_asset_id_candidates(42) == [42]
    assert parse_asset_id_candidates("141,235") == [141, 235]
    assert parse_asset_id_candidates(" 141 , 235 ") == [141, 235]
    assert parse_asset_id_candidates("141,foo,235") == [141, 235]


def test_resolve_prefers_english_then_lowest_id(database: capy.Database):
    model = database.create(
        asset=[
            {"slug": "es-a", "lang": "es", "asset_type": "EXERCISE"},
            {"slug": "us-b", "lang": "us", "asset_type": "EXERCISE"},
        ],
    )
    es_asset, us_asset = model.asset
    assert resolve_asset_id_from_candidates([es_asset.id, us_asset.id]) == us_asset.id
    assert resolve_asset_id_from_payload_value(f"{es_asset.id},{us_asset.id}") == us_asset.id


def test_resolve_multiple_english_picks_lowest_id(database: capy.Database):
    model = database.create(
        asset=[
            {"slug": "en-low", "lang": "en", "asset_type": "EXERCISE"},
            {"slug": "us-high", "lang": "us", "asset_type": "EXERCISE"},
        ],
    )
    a, b = model.asset
    low_id, high_id = (a.id, b.id) if a.id < b.id else (b.id, a.id)
    raw = f"{high_id},{low_id}"
    assert resolve_asset_id_from_payload_value(raw) == low_id
    asset = resolve_asset_from_payload_asset_id(raw)
    assert asset is not None and asset.id == low_id


def test_resolve_non_english_only_picks_lowest_id(database: capy.Database):
    model = database.create(
        asset=[
            {"slug": "es-one", "lang": "es", "asset_type": "EXERCISE"},
            {"slug": "es-two", "lang": "es", "asset_type": "EXERCISE"},
        ],
    )
    x, y = model.asset
    low, high = (x, y) if x.id < y.id else (y, x)
    assert resolve_asset_id_from_payload_value(f"{high.id},{low.id}") == low.id


def test_resolve_unknown_ids_returns_none(database: capy.Database):
    database.create(asset={"slug": "only-one", "lang": "us", "asset_type": "EXERCISE"})
    assert resolve_asset_id_from_candidates([999999991, 999999992]) is None
    assert resolve_asset_id_from_payload_value("999999991,999999992") is None
