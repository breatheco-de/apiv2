"""
Token mixin
"""
import re


class TokenMixin():
    """Token mixin"""

    __token_pattern__ = re.compile(r"^[0-9a-zA-Z]{,40}$")

    def assertToken(self, expected: str):
        """Assert that token is valid format"""
        self.assertTrue(bool(self.__token_pattern__.match(expected)))
