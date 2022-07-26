import os
import pytest
from scripts.utils.environment import reset_environment, test_environment
from breathecode.utils.exceptions import TestError
import numpy as np
from PIL import Image
from faker import Faker

# set ENV as test before run django
os.environ['ENV'] = 'test'

FAKE = Faker()


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


@pytest.fixture()
def random_image(fake):

    filename = fake.slug() + '.png'

    def wrapper(size):
        image = Image.new('RGB', size)
        arr = np.random.randint(low=0, high=255, size=(size[1], size[0]))

        image = Image.fromarray(arr.astype('uint8'))
        image.save(filename, 'PNG')

        file = open(filename, 'rb')

        return file, filename

    yield wrapper

    os.remove(filename)


@pytest.fixture()
def fake():
    return FAKE
