"""
Token mixin
"""

import re

__all__ = ["Sha256Mixin"]


class Sha256Mixin:
    """Token mixin"""

    __hash_pattern__ = re.compile(r"^[0-9a-zA-Z]{,64}$")

    def assertHash(self, expected: str):
        """
        Assert that token is valid format.

        Usage:

        ```py
        rigth_hash = 'f6fc84c9f21c24907d6bee6eec38cabab5fa9a7be8c4a7827fe9e56f245bd2d5'
        bad_hash = 'Potato'

        # pass because is a right hash
        self.bc.check.sha256(rigth_hash)  # 🟢

        # fail because is a bad hash
        self.bc.check.sha256(bad_hash)  # 🔴
        ```
        """
        self.assertTrue(bool(self.__hash_pattern__.match(expected)))
