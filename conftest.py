import pytest


@pytest.fixture(autouse=True)
def no_http_requests(monkeypatch):
    def urlopen_mock(self, method, url, *args, **kwargs):
        raise Exception(
            f'The test was about to {method} {self.scheme}://{self.host}{url} and this is a third party service'
        )

    monkeypatch.setattr('urllib3.connectionpool.HTTPConnectionPool.urlopen', urlopen_mock)
