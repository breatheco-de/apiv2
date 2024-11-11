import os

from capyc.core.managers import feature


@feature.availability("activity.logs")
def enable_activity() -> bool:
    env = os.getenv("ENABLE_ACTIVITY")
    if env is None:
        return True

    return env in feature.TRUE


feature.add(enable_activity)
