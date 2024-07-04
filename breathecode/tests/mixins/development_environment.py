"""
Setup development environment
"""

import os

__all__ = ["DevelopmentEnvironment"]


class DevelopmentEnvironment:
    """Setup ENV variable"""

    def __init__(self):
        os.environ["ENV"] = "development"
