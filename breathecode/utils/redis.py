from django.core.cache import cache

IS_DJANGO_REDIS = hasattr(cache, "fake") is False

__all__ = ["Lock"]

if IS_DJANGO_REDIS:
    from redis.lock import Lock
else:

    class Lock:

        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            pass

        def __exit__(self, *args, **kwargs):
            pass
