"""
Global mixins
"""

from .breathecode import Breathecode, fake

__all__ = ["BreathecodeMixin", "fake"]


class BreathecodeMixin:
    bc: Breathecode

    def set_test_instance(self, parent) -> None:
        self.bc = Breathecode(parent)
