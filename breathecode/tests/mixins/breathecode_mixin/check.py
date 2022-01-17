from ..sha256_mixin import Sha256Mixin
from ..token_mixin import TokenMixin

__all__ = ['Check']


class Check:
    """Wrapper of last implementation for request for testing purposes"""

    sha256 = Sha256Mixin.assertHash
    token = TokenMixin.assertToken

    def __init__(self, parent) -> None:
        self.parent = parent
