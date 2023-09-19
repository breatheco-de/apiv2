from contextlib2 import contextmanager
import pytest

from breathecode.tests.mixins.breathecode_mixin import BreathecodeMixin
from breathecode.tests.mixins.cache_mixin import CacheMixin
from breathecode.tests.mixins.generate_models_mixin.generate_models_mixin import GenerateModelsMixin
from rest_framework.test import APIClient

__all__ = ['LegacyAPITestCase']


class LegacyAPITestCase(BreathecodeMixin, GenerateModelsMixin, CacheMixin):
    """
    This fixture keeps with APITestCase from rest_framework team.
    """

    client: APIClient

    @pytest.fixture(autouse=True)
    def setup(self, db, request):
        # setup logic
        self.client = APIClient()
        self.set_test_instance(request.instance)
        yield
        self.clear_cache()
        # teardown logic

    def assertEqual(self, n1, n2, msg=None):
        if msg:
            assert n1 == n2, msg

        else:
            assert n1 == n2

    @contextmanager
    def assertRaisesMessage(self, expected_exception, expected_message):
        try:
            yield
        except expected_exception as e:
            assert str(e) == expected_message, f"Expected '{expected_message}', but got '{str(e)}'"
        except Exception as e:
            pytest.fail(f'Expected {expected_exception} but it was not raised.')
