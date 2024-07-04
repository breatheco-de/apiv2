"""
Apply ENV=development
"""

import os


class DevelopmentEnvironment:
    """Apply env"""

    def __init__(self):
        os.environ["ENV"] = "development"
