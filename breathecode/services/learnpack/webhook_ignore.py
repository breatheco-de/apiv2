"""
Per-academy LearnPack telemetry webhook ignore rules.

Stored under ``AcademyAuthSettings.learnpack_features[LEARNPACK_FEATURES_TELEMETRY_WEBHOOK_IGNORE_KEY]``.
Matching is OR across dimensions: if any configured list contains a value that matches the
incoming payload, the webhook should not be processed (stored as IGNORED).

``events`` applies to streaming payloads (explicit ``event`` in body). For non-streaming
``batch`` payloads the event dimension is not evaluated (batch root has no single event).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from capyc.rest_framework.exceptions import ValidationException

from breathecode.services.learnpack.resolve_payload_asset import resolve_asset_id_from_payload_value

if TYPE_CHECKING:
    from breathecode.authenticate.models import AcademyAuthSettings

LEARNPACK_FEATURES_TELEMETRY_WEBHOOK_IGNORE_KEY = "telemetry_webhook_ignore"

_TELEMETRY_IGNORE_BODY_KEYS = (
    "user_ids",
    "learnpack_package_ids",
    "package_slugs",
    "asset_ids",
    "events",
)


def get_telemetry_webhook_ignore_from_settings(settings: AcademyAuthSettings) -> dict:
    lf = settings.learnpack_features if isinstance(settings.learnpack_features, dict) else {}
    raw = lf.get(LEARNPACK_FEATURES_TELEMETRY_WEBHOOK_IGNORE_KEY)
    return raw if isinstance(raw, dict) else {}


def validate_telemetry_webhook_ignore_body(body: Any) -> dict:
    if body is None:
        return {}
    if not isinstance(body, dict):
        raise ValidationException(
            "Request body must be a JSON object",
            code=400,
            slug="invalid-telemetry-webhook-ignore-body",
        )
    cleaned: dict[str, list] = {}
    for key in _TELEMETRY_IGNORE_BODY_KEYS:
        if key not in body:
            continue
        value = body[key]
        if value is None:
            continue
        if not isinstance(value, list):
            raise ValidationException(
                f"`{key}` must be a list",
                code=400,
                slug="invalid-telemetry-webhook-ignore-field",
            )
        cleaned[key] = value
    return cleaned


def set_telemetry_webhook_ignore_on_settings(settings: AcademyAuthSettings, cleaned: dict) -> None:
    lf = dict(settings.learnpack_features or {})
    lf[LEARNPACK_FEATURES_TELEMETRY_WEBHOOK_IGNORE_KEY] = cleaned
    settings.learnpack_features = lf
    settings.save(update_fields=["learnpack_features"])


def _coerce_positive_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _int_set_from_config(raw: Any) -> set[int]:
    if not isinstance(raw, list):
        return set()
    out: set[int] = set()
    for item in raw:
        n = _coerce_positive_int(item)
        if n is not None:
            out.add(n)
    return out


def _str_set_from_config(raw: Any) -> set[str]:
    if not isinstance(raw, list):
        return set()
    out: set[str] = set()
    for item in raw:
        if item is None:
            continue
        s = str(item).strip()
        if s:
            out.add(s)
    return out


def _package_id_from_payload(payload: dict) -> int | None:
    raw = payload.get("package_id")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _package_slugs_from_payload(payload: dict) -> set[str]:
    out: set[str] = set()
    for key in ("package_slug", "slug"):
        v = payload.get(key)
        if v is not None:
            s = str(v).strip()
            if s:
                out.add(s)
    return out


def _event_from_payload(payload: dict, is_streaming: bool) -> str | None:
    if not is_streaming:
        return None
    ev = payload.get("event")
    if ev is None:
        return None
    s = str(ev).strip()
    return s or None


def should_ignore_learnpack_webhook(academy_id: int, payload: dict | None) -> tuple[bool, str | None]:
    """
    Return (True, reason) if this academy has a rule that matches ``payload``; else (False, None).

    ``payload`` is the merged telemetry body (same shape as ``LearnPack.add_webhook_to_log`` input).
    """
    if not payload or not isinstance(payload, dict):
        return False, None

    from breathecode.authenticate.models import AcademyAuthSettings

    settings = AcademyAuthSettings.objects.filter(academy_id=academy_id).first()
    if settings is None:
        return False, None

    cfg = get_telemetry_webhook_ignore_from_settings(settings)
    if not cfg:
        return False, None

    user_blocklist = _int_set_from_config(cfg.get("user_ids"))
    package_blocklist = _int_set_from_config(cfg.get("learnpack_package_ids"))
    slug_blocklist = _str_set_from_config(cfg.get("package_slugs"))
    asset_blocklist = _int_set_from_config(cfg.get("asset_ids"))
    event_blocklist = _str_set_from_config(cfg.get("events"))

    if not any(
        (
            user_blocklist,
            package_blocklist,
            slug_blocklist,
            asset_blocklist,
            event_blocklist,
        )
    ):
        return False, None

    is_streaming = "event" in payload

    uid = _coerce_positive_int(payload.get("user_id"))
    if user_blocklist and uid is not None and uid in user_blocklist:
        return True, "Ignored by academy learnpack_features.telemetry_webhook_ignore (user_ids)."

    pkg_id = _package_id_from_payload(payload)
    if package_blocklist and pkg_id is not None and pkg_id in package_blocklist:
        return True, "Ignored by academy learnpack_features.telemetry_webhook_ignore (learnpack_package_ids)."

    payload_slugs = _package_slugs_from_payload(payload)
    if slug_blocklist and payload_slugs & slug_blocklist:
        return True, "Ignored by academy learnpack_features.telemetry_webhook_ignore (package_slugs)."

    resolved_asset = resolve_asset_id_from_payload_value(payload.get("asset_id"))
    if asset_blocklist and resolved_asset is not None and resolved_asset in asset_blocklist:
        return True, "Ignored by academy learnpack_features.telemetry_webhook_ignore (asset_ids)."

    ev = _event_from_payload(payload, is_streaming)
    if event_blocklist and ev is not None and ev in event_blocklist:
        return True, "Ignored by academy learnpack_features.telemetry_webhook_ignore (events)."

    return False, None
