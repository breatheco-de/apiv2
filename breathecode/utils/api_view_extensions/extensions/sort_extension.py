from typing import Any
from breathecode.utils.api_view_extensions.extension_base import ExtensionBase
from breathecode.utils.api_view_extensions.priorities.mutator_order import MutatorOrder
from django.db.models import QuerySet

__all__ = ['SortExtension']

REQUIREMENTS = ['cache']


class SortExtension(ExtensionBase):

    _sort: str

    def __init__(self, sort: str, **kwargs) -> None:
        self._sort = sort

    def _apply_queryset_mutation(self, queryset: QuerySet[Any]):
        queryset = queryset.order_by(self._request.GET.get('sort') or self._sort)
        return queryset

    def _can_modify_queryset(self) -> bool:
        return True

    def _get_order_of_mutator(self) -> int:
        return int(MutatorOrder.SORT)
