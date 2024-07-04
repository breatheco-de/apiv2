from typing import Any


class InvalidTokenType(Exception):

    def __init__(self, *args: Any):
        super().__init__(*args)


class TokenNotFound(Exception):

    def __init__(self, error: str = "Token not found", *args: Any):
        super().__init__(error, *args)


class BadArguments(Exception):

    def __init__(self, *args: Any):
        super().__init__(*args)


class TryToGetOrCreateAOneTimeToken(Exception):

    def __init__(self, *args: Any):
        super().__init__(*args)
