import os

class DevelopmentEnvironment():
    def __init__(self):
        os.environ['ENV'] = 'development'
