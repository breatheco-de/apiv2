from django.core.exceptions import ValidationError

__all__ = ["validate_language_code"]


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
