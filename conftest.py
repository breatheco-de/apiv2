import os
import pytest
from scripts.utils.environment import reset_environment, test_environment
from breathecode.utils.exceptions import TestError

# set ENV as test before run django
os.environ['ENV'] = 'test'


@pytest.fixture(autouse=True)
def no_http_requests(monkeypatch):
    def urlopen_mock(self, method, url, *args, **kwargs):
        # this prevent a tester left pass a request to a third party service
        raise TestError(f'Avoid make a real request to {method} {self.scheme}://{self.host}{url}')

    monkeypatch.setattr('urllib3.connectionpool.HTTPConnectionPool.urlopen', urlopen_mock)


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    reset_environment()
    test_environment()
