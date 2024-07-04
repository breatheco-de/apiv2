import os
from typing import Any, Optional

from django.core.handlers.wsgi import WSGIRequest
from django.db.models import QuerySet
from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response

from breathecode.utils.api_view_extensions.extension_base import ExtensionBase
from breathecode.utils.api_view_extensions.extensions.language_extension import LanguageExtension
from breathecode.utils.api_view_extensions.extensions.lookup_extension import LookupExtension

from .extensions import CacheExtension

__all__ = ["APIViewExtensionHandlers"]
is_test_env = os.getenv("ENV") == "test"


class APIViewExtensionHandlers:
    """A collection of tools that pretend can build extensions globally."""

    # the custom method we want to export go here
    cache: Optional[CacheExtension]
    language: Optional[LanguageExtension]
    lookup: Optional[LookupExtension]

    # internal attrs
    _request: WSGIRequest
    _extensions: set[ExtensionBase]
    _instances: set[ExtensionBase]

    def __init__(self, request: WSGIRequest, valid_extensions: Optional[set[ExtensionBase]] = None, **kwargs):
        """Build the handlers."""

        if valid_extensions is None:
            valid_extensions = []

        self._extensions = valid_extensions
        self._request = request

        self._instances = set()

        for extension in valid_extensions:
            instance = extension(**kwargs)
            instance._set_request(request)
            instance._optional_dependencies(**kwargs)
            self._instances.add(instance)

            if name := instance._instance_name():
                setattr(self, name, instance)

        if is_test_env:
            self._register_valid_extensions()
            self._spy_extension_arguments(**kwargs)

    def queryset(self, queryset: QuerySet[Any]) -> QuerySet[Any]:
        """Apply mutations over queryset."""

        # The extension can decide if act or not
        extensions_allowed = [
            x for x in self._instances if x._can_modify_queryset() and x._get_order_of_mutator() != -1
        ]

        extensions = sorted(extensions_allowed, key=lambda x: x._get_order_of_mutator())
        for extension in extensions:
            queryset = extension._apply_queryset_mutation(queryset)

        return queryset

    def response(self, data: dict | list[dict], format="application/json"):
        """Get the response of endpoint."""

        headers = {}

        # The extension can decide if act or not
        extensions_allowed = [
            x for x in self._instances if x._can_modify_response() and x._get_order_of_response() != -1
        ]

        extensions = sorted(extensions_allowed, key=lambda x: x._get_order_of_response())
        for extension in extensions:
            data, headers = extension._apply_response_mutation(data, headers, format)

        if isinstance(data, str) or isinstance(data, bytes):
            return HttpResponse(data, status=status.HTTP_200_OK, headers=headers)

        return Response(data, status=status.HTTP_200_OK, headers=headers)

    def _register_valid_extensions(self) -> None:
        self._spy_extensions(sorted([x.__name__ for x in self._extensions]))

    def _spy_extensions(self, _: list[str]) -> None:
        """Spy the extensions is being used in the tests."""
        ...

    def _spy_extension_arguments(self, **_) -> None:
        """Spy the extension arguments is being used in the tests."""
        ...
