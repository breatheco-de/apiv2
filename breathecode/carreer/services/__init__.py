import logging
from django.contrib import messages
from .base_scraper import *

logger = logging.getLogger(__name__)


def ScraperFactory(service: str):
    import importlib
    try:
        return getattr(importlib.import_module('breathecode.carreer.services.' + service.lower()),
                       service.capitalize() + 'Scraper')
    except Exception as e:
        logger.error(f'There was an error import the library - {str(e)}')
