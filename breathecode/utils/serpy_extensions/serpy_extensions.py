from .extensions import DatetimeIntegerField

__all__ = ["SerpyExtensions"]


class SerpyExtensions:

    @staticmethod
    def DatetimeIntegerField(*args, **kwargs):  # noqa: N802
        return DatetimeIntegerField(*args, **kwargs)
