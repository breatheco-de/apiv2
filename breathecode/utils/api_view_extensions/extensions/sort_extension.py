from typing import Any

from django.db.models import QuerySet

from breathecode.utils.api_view_extensions.extension_base import ExtensionBase
from breathecode.utils.api_view_extensions.priorities.mutator_order import MutatorOrder
from breathecode.utils.generate_lookups_mixin import GenerateLookupsMixin

__all__ = ["SortExtension"]

REQUIREMENTS = ["cache"]


class SortExtension(ExtensionBase, GenerateLookupsMixin):

    _sort: str

    def __init__(self, sort: str, **kwargs) -> None:
        self._sort = sort

    def _apply_queryset_mutation(self, queryset: QuerySet[Any]):
        lookups = self.generate_lookups(self._request, many_fields=["sort"])
        sort_in = lookups["sort__in"] if "sort__in" in lookups else ""
        if len(sort_in) != 0:
            queryset = queryset.order_by(*sort_in or self._sort)
        else:
            queryset = queryset.order_by(self._request.GET.get("sort") or self._sort)
        return queryset

    def _can_modify_queryset(self) -> bool:
        return True

    def _get_order_of_mutator(self) -> int:
        return int(MutatorOrder.SORT)
