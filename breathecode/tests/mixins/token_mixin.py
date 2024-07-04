"""
Token mixin
"""

import re

__all__ = ["TokenMixin"]


class TokenMixin:
    """Token mixin"""

    __token_pattern__ = re.compile(r"^[0-9a-zA-Z]{,40}$")

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
        self.assertTrue(bool(self.__token_pattern__.match(expected)))
