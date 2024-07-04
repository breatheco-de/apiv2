__all__ = ["make_method", "change_field"]


def make_method(status, name):

    def _method(modeladmin, request, queryset):
        val = {}
        val[name] = status
        queryset.update(**val)

    return _method


def change_field(possible_status, name="status"):
    methods = []
    for status in possible_status:
        _method = make_method(status, name)
        _method.__name__ = "change_" + name + "_" + status
        methods.append(_method)
    return methods
