from serpy.fields import Field

__all__ = ["ManyToManyField"]


class ManyToManyField(Field):
    getter_takes_serializer = False

    def __init__(self, serializer, attr=None, call=False, label=None, required=True, **kwargs):
        self.real_attr = serializer.attr
        self.attr = None
        super().__init__(None, call, label, required)

        serializer.many = True
        self.serializer = serializer
        self.many = True

    def as_getter(self, serializer_field_name, serializer_cls):
        handler = self.handler
        return lambda *args, **kwargs: handler(*args, **kwargs)

    def handler(self, obj):
        # return []
        queryset = getattr(obj, self.real_attr).all()
        return self.serializer.__class__(queryset, many=True).data
