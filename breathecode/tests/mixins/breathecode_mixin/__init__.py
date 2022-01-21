"""
Global mixins
"""
from .breathecode import Breathecode

__all__ = ['BreathecodeMixin']


class BreathecodeMixin():
    bc: Breathecode

    def set_test_instance(self, parent) -> None:
        self.bc = Breathecode(parent)
