from types import SimpleNamespace

from breathecode.registry.utils import compute_asset_error_log_dedupe_merge


def test_compute_asset_error_log_dedupe_merge_status_priority():
    keeper = SimpleNamespace(status="IGNORED", status_text=None, user_id=None, priority=1)
    duplicates = [
        SimpleNamespace(status="FIXED", status_text="a", user_id=2, priority=2),
        SimpleNamespace(status="ERROR", status_text="b", user_id=3, priority=3),
    ]

    merged = compute_asset_error_log_dedupe_merge(keeper, duplicates)

    assert merged["status"] == "ERROR"
    assert merged["priority"] == 3
    assert merged["user_id"] == 3
    assert merged["status_text"] == "b"


def test_compute_asset_error_log_dedupe_merge_keeps_keeper_status_text():
    keeper = SimpleNamespace(status="ERROR", status_text="keeper", user_id=None, priority=1)
    duplicates = [SimpleNamespace(status="FIXED", status_text="dup", user_id=2, priority=9)]

    merged = compute_asset_error_log_dedupe_merge(keeper, duplicates)

    assert merged["status_text"] == "keeper"


def test_compute_asset_error_log_dedupe_merge_fills_missing_status_text_from_last_duplicate():
    keeper = SimpleNamespace(status="ERROR", status_text=None, user_id=None, priority=1)
    duplicates = [
        SimpleNamespace(status="FIXED", status_text="first", user_id=None, priority=1),
        SimpleNamespace(status="IGNORED", status_text="last", user_id=None, priority=1),
    ]

    merged = compute_asset_error_log_dedupe_merge(keeper, duplicates)

    assert merged["status_text"] == "last"
