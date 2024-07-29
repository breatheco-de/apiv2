"""
Celery Mocks
"""

from unittest.mock import Mock
from .shared_task_mock import shared_task

CELERY_PATH = {
    "shared_task": "celery.shared_task",
}

CELERY_INSTANCES = {
    "shared_task": Mock(side_effect=shared_task),
}


def apply_celery_shared_task_mock():
    """Apply Storage Blob Mock"""
    return CELERY_INSTANCES["shared_task"]
