"""
Token mixin
"""
import re

class TokenMixin():
    """Token mixin"""

    token_pattern = re.compile(r"^[0-9a-zA-Z]{,40}$")

    def assertToken(self, expected: str):
        """Assert that token is valid format"""
        self.assertEqual(bool(self.token_pattern.match(expected)), True)
