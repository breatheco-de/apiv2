from django.core.exceptions import ValidationError

__all__ = ["validate_language_code", "languages_equivalent", "language_codes_for_lookup"]


def languages_equivalent(lang_a: str | None, lang_b: str | None) -> bool:
    """
    Return True if both codes refer to the same language (e.g. 'us' and 'en').
    Case-insensitive; handles None/empty.
    """
    a = (lang_a or "").strip().lower()
    b = (lang_b or "").strip().lower()
    if a == b:
        return True
    return (a, b) in (("us", "en"), ("en", "us"))


def language_codes_for_lookup(lang: str | None) -> list[str]:
    """
    Return codes to use when querying by language (e.g. filter(lang__in=...)).
    For 'us' or 'en' returns ['us', 'en']; otherwise [normalized_lang]; None/empty -> [].
    """
    if not lang:
        return []
    normalized = lang.strip().lower()
    if not normalized:
        return []
    if normalized in ("us", "en"):
        return ["us", "en"]
    return [normalized]


def validate_language_code(value: str | None) -> None:
    is_short = len(value) == 2

    if value and len(value) != 2 and len(value) != 5:
        raise ValidationError(
            "Language code must be 2 or 5 chars long",
            params={"value": value},
        )

    if value and value[:2].isupper():
        raise ValidationError(f"{value} the first two letters needs to be lowercase")

    if value and not is_short and value[2] != "-":
        raise ValidationError(f"{value} the third letter needs to be a dash")

    if value and not is_short and value[3:].islower():
        raise ValidationError(f"{value} the last two letters needs to be uppercase")
