import logging
from .base_scraper import *  # noqa: F401

logger = logging.getLogger(__name__)


def scraper_factory(service: str):
    import importlib

    try:
        return getattr(
            importlib.import_module("breathecode.career.services." + service.lower()), service.capitalize() + "Scraper"
        )
    except Exception as e:
        logger.error(f"There was an error import the library - {str(e)}")
