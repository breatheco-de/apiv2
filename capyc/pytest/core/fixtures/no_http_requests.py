import pytest

__all__ = ["no_http_requests"]


@pytest.fixture(scope="module")
def no_http_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    from urllib3.connectionpool import HTTPConnectionPool

    urlopen = HTTPConnectionPool.urlopen

    def urlopen_mock(self, method, url, *args, **kwargs):
        # this prevent a tester left pass a request to a third party service
        allow = [
            ("0.0.0.0", 9050, None),
        ]

        for host, port, path in allow:
            if host == self.host and port == self.port and (path == url or path == None):
                return urlopen(self, method, url, *args, **kwargs)

        raise Exception(
            f"All HTTP request to third party services are forwidden, {method.upper()} {self.scheme}://{self.host}{url}"
        )

    monkeypatch.setattr("urllib3.connectionpool.HTTPConnectionPool.urlopen", urlopen_mock)
