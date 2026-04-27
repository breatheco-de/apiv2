"""
Per-academy LearnPack telemetry webhook ignore rules.

Stored under ``AcademyAuthSettings.learnpack_features[LEARNPACK_FEATURES_TELEMETRY_WEBHOOK_IGNORE_KEY]``.

Preferred shape supports rule combinations:

{
  "rules": [
    {"events": ["batch"], "learnpack_package_ids": [13190]},
    {"user_ids": [42]}
  ]
}

Each rule is AND across provided fields; each list is OR within that field; top-level rules are OR.

Legacy shape (top-level lists without ``rules``) is still accepted and keeps previous OR semantics.
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
    cleaned: dict[str, Any] = {}

    rules = body.get("rules")
    if rules is not None:
        if not isinstance(rules, list):
            raise ValidationException(
                "`rules` must be a list",
                code=400,
                slug="invalid-telemetry-webhook-ignore-field",
            )
        cleaned_rules: list[dict[str, list]] = []
        for idx, rule in enumerate(rules):
            if not isinstance(rule, dict):
                raise ValidationException(
                    f"`rules[{idx}]` must be an object",
                    code=400,
                    slug="invalid-telemetry-webhook-ignore-field",
                )
            cleaned_rule = _clean_rule_dict(rule)
            if cleaned_rule:
                cleaned_rules.append(cleaned_rule)
        cleaned["rules"] = cleaned_rules

    # Backward-compatible top-level legacy keys.
    for key in _TELEMETRY_IGNORE_BODY_KEYS:
        if key in body:
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


def _clean_rule_dict(raw: dict) -> dict[str, list]:
    cleaned: dict[str, list] = {}
    for key in _TELEMETRY_IGNORE_BODY_KEYS:
        if key not in raw:
            continue
        value = raw[key]
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


def _match_rule_all_fields(payload: dict, rule: dict[str, Any]) -> str | None:
    # For a combined rule, every configured field must match.
    uid = _coerce_positive_int(payload.get("user_id"))
    pkg_id = _package_id_from_payload(payload)
    payload_slugs = _package_slugs_from_payload(payload)
    resolved_asset = resolve_asset_id_from_payload_value(payload.get("asset_id"))
    is_streaming = "event" in payload
    event_value = _event_from_payload(payload, is_streaming)

    if "user_ids" in rule:
        block = _int_set_from_config(rule.get("user_ids"))
        if uid is None or uid not in block:
            return None
    if "learnpack_package_ids" in rule:
        block = _int_set_from_config(rule.get("learnpack_package_ids"))
        if pkg_id is None or pkg_id not in block:
            return None
    if "package_slugs" in rule:
        block = _str_set_from_config(rule.get("package_slugs"))
        if not (payload_slugs & block):
            return None
    if "asset_ids" in rule:
        block = _int_set_from_config(rule.get("asset_ids"))
        if resolved_asset is None or resolved_asset not in block:
            return None
    if "events" in rule:
        block = _str_set_from_config(rule.get("events"))
        if event_value is None or event_value not in block:
            return None

    fields = ",".join([k for k in _TELEMETRY_IGNORE_BODY_KEYS if k in rule]) or "rule"
    return f"Ignored by academy learnpack_features.telemetry_webhook_ignore rule ({fields})."


def _match_legacy_any(payload: dict, cfg: dict[str, Any]) -> str | None:
    user_blocklist = _int_set_from_config(cfg.get("user_ids"))
    package_blocklist = _int_set_from_config(cfg.get("learnpack_package_ids"))
    slug_blocklist = _str_set_from_config(cfg.get("package_slugs"))
    asset_blocklist = _int_set_from_config(cfg.get("asset_ids"))
    event_blocklist = _str_set_from_config(cfg.get("events"))

    if not any((user_blocklist, package_blocklist, slug_blocklist, asset_blocklist, event_blocklist)):
        return None

    is_streaming = "event" in payload
    uid = _coerce_positive_int(payload.get("user_id"))
    if user_blocklist and uid is not None and uid in user_blocklist:
        return "Ignored by academy learnpack_features.telemetry_webhook_ignore (user_ids)."

    pkg_id = _package_id_from_payload(payload)
    if package_blocklist and pkg_id is not None and pkg_id in package_blocklist:
        return "Ignored by academy learnpack_features.telemetry_webhook_ignore (learnpack_package_ids)."

    payload_slugs = _package_slugs_from_payload(payload)
    if slug_blocklist and payload_slugs & slug_blocklist:
        return "Ignored by academy learnpack_features.telemetry_webhook_ignore (package_slugs)."

    resolved_asset = resolve_asset_id_from_payload_value(payload.get("asset_id"))
    if asset_blocklist and resolved_asset is not None and resolved_asset in asset_blocklist:
        return "Ignored by academy learnpack_features.telemetry_webhook_ignore (asset_ids)."

    ev = _event_from_payload(payload, is_streaming)
    if event_blocklist and ev is not None and ev in event_blocklist:
        return "Ignored by academy learnpack_features.telemetry_webhook_ignore (events)."

    return None


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

    # New combined rules syntax.
    rules = cfg.get("rules")
    if isinstance(rules, list):
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            reason = _match_rule_all_fields(payload, rule)
            if reason:
                return True, reason

    # Backward-compatible legacy syntax.
    reason = _match_legacy_any(payload, cfg)
    if reason:
        return True, reason

    return False, None
