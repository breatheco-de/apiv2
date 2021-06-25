"""
Token mixin
"""
import re


class Sha256Mixin():
    """Token mixin"""

    __hash_pattern__ = re.compile(r"^[0-9a-zA-Z]{,64}$")

    def assertHash(self, expected: str):
        """Assert that token is valid format"""
        self.assertTrue(bool(self.__hash_pattern__.match(expected)))
