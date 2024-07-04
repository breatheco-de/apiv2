"""
Google Cloud Storage Mocks
"""

from unittest.mock import MagicMock

LOGGING_PATH = {
    "logger": "logging.Logger",
}

LOGGING_INSTANCES = {"logger": MagicMock()}


def apply_logging_logger_mock():
    """Apply Storage Blob Mock"""
    return LOGGING_INSTANCES["logger"]
