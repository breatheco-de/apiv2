"""
Global mixins
"""
from .breathecode import Breathecode

__all__ = ['BreathecodeMixin']


class BreathecodeMixin():
    bc = Breathecode()
