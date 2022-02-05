from serpy.fields import Field

from ...datetime_interger import DatetimeInteger

__all__ = ['DatetimeIntegerField']


class DatetimeIntegerField(Field):
    getter_takes_serializer = True

    def __init__(self, method=None, **kwargs):
        super(DatetimeIntegerField, self).__init__(**kwargs)
        self.method = method

    def as_getter(self, serializer_field_name, serializer_cls):
        method_name = self.method

        if method_name is None:
            method_name = 'get_{0}'.format(serializer_field_name)

        wrapper = self.__datetime_interger__
        handler = lambda self, obj: wrapper(serializer_field_name, obj)
        setattr(serializer_cls, method_name, handler)
        return getattr(serializer_cls, method_name)

    def __datetime_interger__(self, key, obj):
        interger = getattr(obj, key)
        timezone = obj.timezone
        return DatetimeInteger.to_iso_string(timezone, interger)
