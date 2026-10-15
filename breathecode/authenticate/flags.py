import os

from capyc.core.managers import feature

flags = feature._flags


@feature.availability("authenticate.set_google_credentials")
def set_google_credentials() -> bool:
    if os.environ.get("SET_GOOGLE_CREDENTIALS") in feature.TRUE:
        return True

    return False


@feature.availability("authenticate.rate_limit")
def rate_limit(scope: str) -> bool:
    enabled = os.environ.get("RATE_LIMIT_ENABLED")
    if enabled is not None and enabled not in feature.TRUE:
        return False

    disabled_scopes = os.environ.get("RATE_LIMIT_DISABLED_SCOPES", "")
    return scope not in [x.strip() for x in disabled_scopes.split(",") if x.strip()]


feature.add(set_google_credentials, rate_limit)
