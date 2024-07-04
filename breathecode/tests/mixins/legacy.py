import re
from contextlib2 import contextmanager
import pytest

from breathecode.tests.mixins.breathecode_mixin import BreathecodeMixin
from breathecode.tests.mixins.cache_mixin import CacheMixin
from breathecode.tests.mixins.generate_models_mixin.generate_models_mixin import GenerateModelsMixin
from rest_framework.test import APIClient

__all__ = ["LegacyAPITestCase"]

token_pattern = re.compile(r"^[0-9a-zA-Z]{,40}$")


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

    def assertEqual(self, arg1, arg2, msg=None):
        if msg:
            assert arg1 == arg2, msg

        else:
            assert arg1 == arg2

    def assertGreater(self, arg1, arg2, msg=None):
        if msg:
            assert arg1 > arg2, msg

        else:
            assert arg1 > arg2

    def assertLess(self, arg1, arg2, msg=None):
        if msg:
            assert arg1 < arg2, msg

        else:
            assert arg1 < arg2

    @contextmanager
    def assertRaisesMessage(self, expected_exception, expected_message):
        try:
            yield
        except expected_exception as e:
            assert str(e) == expected_message, f"Expected '{expected_message}', but got '{str(e)}'"
        except Exception as e:
            pytest.fail(f"Expected {expected_exception} but it was not raised.")

    def assertToken(self, expected: str):
        """
        Assert that token have a valid format.

        Usage:

        ```py
        rigth_token = 'f6fc84c9f21c24907d6bee6eec38cabab5fa9a7be8c4a7827fe9e56f245bd2d5'
        bad_token = 'Potato'

        # pass because is a right token
        self.bc.check.token(rigth_hash)  # 🟢

        # fail because is a bad token
        self.bc.check.token(bad_hash)  # 🔴
        ```
        """
        assert bool(token_pattern.match(expected))
