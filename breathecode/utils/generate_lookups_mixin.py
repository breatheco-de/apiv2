from django.core.handlers.wsgi import WSGIRequest
from rest_framework.exceptions import APIException

__all__ = ["GenerateLookupsMixin"]


class GenerateLookupsMixin(APIException):

    def __field_exists__(self, request: WSGIRequest, field: str):
        return field in request.GET

    def __field_name__(self, field: str, pk=False, many=False):
        if pk:
            # `pk` allow custom primary keys, don't use `id`
            field = f"{field}__pk"

        if many:
            field = f"{field}__in"

        return field

    def __field_value__(self, request: WSGIRequest, field: str, many=False):
        value = request.GET.get(field)

        if many:
            value = value.split(",")
        return value

    def __bulk_generator__(self, request: WSGIRequest, fields: list[str], pk=False, many=False):
        return [
            (self.__field_name__(field, pk=pk, many=many), self.__field_value__(request, field, many=many))
            for field in fields
            if self.__field_exists__(request, field)
        ]

    def generate_lookups(
        self, request: WSGIRequest, fields=None, relationships=None, many_fields=None, many_relationships=None
    ):
        """Get the variables through of querystring, returns one list ready to be used by the filter method."""

        if fields is None:
            fields = []

        if relationships is None:
            relationships = []

        if many_fields is None:
            many_fields = []

        if many_relationships is None:
            many_relationships = []

        kwargs = {}
        founds = (
            self.__bulk_generator__(request, fields)
            + self.__bulk_generator__(request, many_fields, many=True)
            + self.__bulk_generator__(request, relationships, pk=True)
            + self.__bulk_generator__(request, many_relationships, pk=True, many=True)
        )

        for field, value in founds:
            kwargs[field] = value

        return kwargs
