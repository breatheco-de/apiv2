"""
Collections of mixins used to login in authorize microservice
"""

import os


class DevelopmentEnvironment:

    def __init__(self):
        os.environ["ENV"] = "development"
