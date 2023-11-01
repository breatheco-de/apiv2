import re
import json
from django.core.cache import cache
import pytest
from breathecode.admissions.caches import CohortCache
from breathecode.events.caches import EventCache
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

cohort_cache = CohortCache()
event_cache = EventCache()

CACHE = {'Cohort': CohortCache, 'Event': EventCache}


def to_snake_case(name):
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()


@pytest.fixture(autouse=True)
def setup(db):
    yield


def test_post_save__create__cohort(bc: Breathecode, enable_signals):
    enable_signals()

    cache.clear()

    models = ['Cohort', 'Event']

    for model in models:
        cases = [[], [{'x': 1}], [{'x': 1}, {'x': 2}]]
        attr = to_snake_case(model)
        lookups = {attr: 1}

        for expected in cases:

            json_data = json.dumps(expected)
            cache.set(
                f'{model}__keys', f'["{model}__", "{model}__sort=slug&slug=100%2C101%2C110%2C111", '
                f'"{model}__id=1", "{model}__id=2"]')

            cache.set(f'{model}__', json_data)
            cache.set(f'{model}__sort=slug&slug=100%2C101%2C110%2C111', json_data)
            cache.set(f'{model}__id=1', json_data)
            cache.set(f'{model}__id=2', json_data)

            bc.database.create(**lookups)

            assert CACHE[model].keys() == []

            assert cache.get(f'{model}__') == None
            assert cache.get(f'{model}__sort=slug&slug=100%2C101%2C110%2C111') == None
            assert cache.get(f'{model}__id=1') == None
            assert cache.get(f'{model}__id=2') == None


# test cohort with a deep of 3
def test_post_save__update__cohort(bc: Breathecode, enable_signals):
    enable_signals()

    cache.clear()

    models = ['Cohort', 'Event']

    for model in models:
        cases = [[], [{'x': 1}], [{'x': 1}, {'x': 2}]]
        attr = to_snake_case(model)
        lookups = {attr: 1}

        for expected in cases:

            json_data = json.dumps(expected)
            cache.set(
                f'{model}__keys', f'["{model}__", "{model}__sort=slug&slug=100%2C101%2C110%2C111", '
                f'"{model}__id=1", "{model}__id=2"]')

            cache.set(f'{model}__', json_data)
            cache.set(f'{model}__sort=slug&slug=100%2C101%2C110%2C111', json_data)
            cache.set(f'{model}__id=1', json_data)
            cache.set(f'{model}__id=2', json_data)

            bc.database.create(**lookups)

            assert CACHE[model].keys() == []

            assert cache.get(f'{model}__') == None
            assert cache.get(f'{model}__sort=slug&slug=100%2C101%2C110%2C111') == None
            assert cache.get(f'{model}__id=1') == None
            assert cache.get(f'{model}__id=2') == None
