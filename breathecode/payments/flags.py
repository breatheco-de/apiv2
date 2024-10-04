from typing import Optional

from capyc.core.managers import feature

from breathecode.authenticate.models import User
from breathecode.utils.decorators.consume import ServiceContext

flags = feature.flags


@feature.availability("payments.bypass_consumption")
def bypass_consumption(context: ServiceContext, user: Optional[User] = None) -> bool:
    """
    This flag is used to bypass the consumption of a service.

    Arguments:
        context: ServiceContext - The context of the service.
        user: Optional[User] - The user to bypass the consumption for, if none it will use request.user.
    """

    if flags.get("BYPASS_CONSUMPTION") not in feature.TRUE:
        return False

    # write logic here

    return False


feature.add(bypass_consumption)
