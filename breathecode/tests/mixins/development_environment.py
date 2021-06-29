"""
Setup development environment
"""
import os


class DevelopmentEnvironment():
    """Setup ENV variable"""
    def __init__(self):
        os.environ['ENV'] = 'development'
