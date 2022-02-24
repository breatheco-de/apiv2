from .base_scrapper import *


def ScraperFactory(service: str):
    import logging
    import importlib
    logger = logging.getLogger(__name__)
    try:
        return getattr(importlib.import_module('breathecode.jobs.services.' + service.lower()),
                       service.capitalize() + 'Scrapper')
    except Exception as e:
        logger.error(f'There was an error import the library {str(e)}')
