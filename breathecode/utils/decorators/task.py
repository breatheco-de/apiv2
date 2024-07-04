import logging
from datetime import timedelta

from task_manager.core.settings import set_settings

__all__ = ["TaskPriority"]

logger = logging.getLogger(__name__)
RETRIES_LIMIT = 10
RETRY_AFTER = timedelta(seconds=5)

from enum import Enum


# keeps this sorted by priority
# unused: ACTIVITY, TWO_FACTOR_AUTH
class TaskPriority(Enum):
    BACKGROUND = 0  # anything without importance
    NOTIFICATION = 1  # non realtime notifications
    MONITORING = 2  # monitoring tasks
    ACTIVITY = 2  # user activity
    CONTENT = 2  # related to the registry
    BILL = 2  # postpaid billing
    ASSESSMENT = 2  # user assessment
    CACHE = 3  # cache
    MARKETING = 4  # marketing purposes
    OAUTH_CREDENTIALS = 5  # oauth tasks
    DEFAULT = 5  # default priority
    TASK_MANAGER = 6  # task manager
    ACADEMY = 7  # anything that the academy can see
    CERTIFICATE = 8  # issuance of certificates
    STUDENT = 9  # anything that the student can see
    TWO_FACTOR_AUTH = 9  # 2fa
    REALTIME = 9  # schedule as soon as possible
    WEB_SERVICE_PAYMENT = 10  # payment in the web
    FIXER = 10  # fixes
    SCHEDULER = 10  # fixes


settings = {
    "RETRIES_LIMIT": 10,
    "RETRY_AFTER": timedelta(seconds=5),
    "DEFAULT": TaskPriority.DEFAULT.value,
    "SCHEDULER": TaskPriority.SCHEDULER.value,
    "TASK_MANAGER": TaskPriority.TASK_MANAGER.value,
}

set_settings(**settings)
