from .base_scrapper import *


def ScraperFactory(service: str):
    import importlib
    return getattr(importlib.import_module('breathecode.jobs.services.' + service.lower()),
                   service.capitalize() + 'Scrapper')
