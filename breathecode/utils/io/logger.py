import os
from logging import Logger as BaseLogger
from logging import getLogger as getBaseLogger
from logging import root
from typing import Annotated, Optional

IS_TEST_ENV = "ENV" in os.environ and os.environ["ENV"] == "test"

__all__ = ["getLogger", "Logger"]

Base = Annotated[BaseLogger, "The original Logger"]


def getLogger(name: Optional[str] = None):  # noqa: N802
    if not name or isinstance(name, str) and name == root.name:
        return root
    base = BaseLogger.manager.getLogger(name)
    logger = Logger(base)
    return logger


# Keep the original docstring
getLogger.__doc__ = getBaseLogger.__doc__


class Logger:
    """Wrapper of Logger module that provide print the slug instead of a message in a test environment."""

    _base: Base

    def __init__(self, base: Base) -> None:
        self._base = base

    def debug(self, msg, *args, slug=None, **kwargs):
        if IS_TEST_ENV and slug:
            self._base.debug(slug, *args, **kwargs)
        else:
            self._base.debug(msg, *args, **kwargs)

    def info(self, msg, *args, slug=None, **kwargs):
        if IS_TEST_ENV and slug:
            self._base.info(slug, *args, **kwargs)
        else:
            self._base.info(msg, *args, **kwargs)

    def warning(self, msg, *args, slug=None, **kwargs):
        if IS_TEST_ENV and slug:
            self._base.warning(slug, *args, **kwargs)
        else:
            self._base.warning(msg, *args, **kwargs)

    def warn(self, msg, *args, slug=None, **kwargs):
        if IS_TEST_ENV and slug:
            self._base.warn(slug, *args, **kwargs)
        else:
            self._base.warn(msg, *args, **kwargs)

    def error(self, msg, *args, slug=None, **kwargs):
        if IS_TEST_ENV and slug:
            self._base.error(slug, *args, **kwargs)
        else:
            self._base.error(msg, *args, **kwargs)

    def exception(self, msg, *args, slug=None, exc_info=True, **kwargs):
        if IS_TEST_ENV and slug:
            self._base.exception(slug, *args, exc_info=exc_info, **kwargs)
        else:
            self._base.exception(msg, *args, exc_info=exc_info, **kwargs)

    def critical(self, msg, *args, slug=None, **kwargs):
        if IS_TEST_ENV and slug:
            self._base.critical(slug, *args, **kwargs)
        else:
            self._base.critical(msg, *args, **kwargs)

    def fatal(self, msg, *args, slug=None, **kwargs):
        if IS_TEST_ENV and slug:
            self._base.fatal(slug, *args, **kwargs)
        else:
            self._base.fatal(msg, *args, **kwargs)

    def log(self, level, msg, *args, slug=None, **kwargs):
        if IS_TEST_ENV and slug:
            self._base.log(level, slug, *args, **kwargs)
        else:
            self._base.log(level, msg, *args, **kwargs)


# Keep the original docstring
Logger.debug.__doc__ = BaseLogger.debug.__doc__
Logger.info.__doc__ = BaseLogger.info.__doc__
Logger.warning.__doc__ = BaseLogger.warning.__doc__
Logger.warn.__doc__ = BaseLogger.warn.__doc__
Logger.error.__doc__ = BaseLogger.error.__doc__
Logger.exception.__doc__ = BaseLogger.exception.__doc__
Logger.critical.__doc__ = BaseLogger.critical.__doc__
Logger.fatal.__doc__ = BaseLogger.fatal.__doc__
Logger.log.__doc__ = BaseLogger.log.__doc__
