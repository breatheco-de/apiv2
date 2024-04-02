import logging

from breathecode.utils.decorators import PermissionContextType

logger = logging.getLogger(__name__)


def code_revision_service(context: PermissionContextType, args: tuple, kwargs: dict) -> tuple[dict, tuple, dict]:

    context['consumables'] = context['consumables'].filter(service_set__slug='code_revision')
    return (context, args, kwargs)
