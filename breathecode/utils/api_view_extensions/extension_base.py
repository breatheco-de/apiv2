from typing import Optional

from django.core.handlers.wsgi import WSGIRequest
from django.db.models import QuerySet


class ExtensionBase:
    _request: WSGIRequest

    def _can_modify_queryset(self) -> bool:
        return False

    def _can_modify_response(self) -> bool:
        return False

    def _instance_name(self) -> Optional[str]:
        return None

    def _get_order_of_mutator(self) -> int:
        return -1

    def _get_order_of_response(self) -> int:
        return -1

    def _apply_queryset_mutation(self, queryset: QuerySet[any]) -> QuerySet[any]:
        raise NotImplementedError()

    def _apply_response_mutation(self, queryset: QuerySet[any]) -> QuerySet[any]:
        raise NotImplementedError()

    def _set_request(self, request: WSGIRequest) -> None:
        self._request = request

    def _optional_dependencies(self, **kwargs) -> None: ...

    def __str__(self) -> str:
        return self.__class__.__name__
