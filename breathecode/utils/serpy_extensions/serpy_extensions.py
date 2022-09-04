from .extensions import DatetimeIntegerField

__all__ = ['SerpyExtensions']


class SerpyExtensions():

    @staticmethod
    def DatetimeIntegerField(*args, **kwargs):
        return DatetimeIntegerField(*args, **kwargs)
