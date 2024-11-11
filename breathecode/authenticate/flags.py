import os

from capyc.core.managers import feature

flags = feature.flags


@feature.availability("authenticate.set_google_credentials")
def set_google_credentials() -> bool:
    if os.getenv("SET_GOOGLE_CREDENTIALS") in feature.TRUE:
        return True

    return False


feature.add(set_google_credentials)
