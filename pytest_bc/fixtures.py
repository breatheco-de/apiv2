from typing import Any, Generator

import pytest
from django.db.models.query import QuerySet
from faker import Faker

FAKE = Faker()


@pytest.fixture(scope='module')
def fake() -> Generator[Faker, None, None]:
    return FAKE


@pytest.fixture(scope='module')
def queryset_with_pks(query: Any, pks: list[int]) -> None:
    """
    Check if the queryset have the following primary keys.

    Usage:

    ```py
    from breathecode.admissions.models import Cohort, Academy

    self.bc.database.create(cohort=1)

    collection = []
    queryset = Cohort.objects.filter()

    # pass because the QuerySet has the primary keys 1
    self.bc.check.queryset_with_pks(queryset, [1])  # 🟢

    # fail because the QuerySet has the primary keys 1 but the second argument is empty
    self.bc.check.queryset_with_pks(queryset, [])  # 🔴
    ```
    """

    assert isinstance(query, QuerySet), 'The first argument is not a QuerySet'

    assert [x.pk for x in query] == pks
