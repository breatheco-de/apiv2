"""
QuerySet fixtures.
"""

from typing import Any, Generator, final

import pytest
from django.db.models.query import QuerySet as DjangoQuerySet

__all__ = ["QuerySet", "queryset"]


@final
class QuerySet:
    """
    QuerySet utils.
    """

    def with_pks(self, query: DjangoQuerySet, pks: list[int]) -> None:
        """
        Assert that the queryset has the following primary keys.

        Usage:

        ```py
        from breathecode.admissions.models import Cohort

        database.create(cohort=1)
        qs = Cohort.objects.filter()

        # pass because the QuerySet has the primary keys 1
        queryset.with_pks(qs, [1])  # 🟢

        # fail because the QuerySet has the primary keys 1 but the second argument is empty
        queryset.with_pks(qs, [])  # 🔴
        ```
        """

        assert isinstance(query, DjangoQuerySet), "The first argument is not a QuerySet"

        assert [x.pk for x in query] == pks

    def get_pks(self, queryset: DjangoQuerySet) -> list[Any]:
        """
        Get the queryset pks.

        Usage:

        ```py
        from breathecode.admissions.models import Cohort

        database.create(cohort=1)
        qs = Cohort.objects.filter()

        assert queryset.get_pks(qs) == [1]
        ```
        """

        return [x.pk for x in queryset]


@pytest.fixture(scope="module")
def queryset() -> Generator[QuerySet, None, None]:
    """
    QuerySet utils.
    """

    yield QuerySet()
