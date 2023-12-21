import logging
from breathecode.utils.decorators import PermissionContextType

logger = logging.getLogger(__name__)


def code_revision_service(context: PermissionContextType, args: tuple,
                          kwargs: dict) -> tuple[dict, tuple, dict]:

    context['consumables'] = context['consumables'].filter(app_service__service='code_revision')
    return (context, args, kwargs)
