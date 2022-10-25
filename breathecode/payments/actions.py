from dateutil.relativedelta import relativedelta

from .models import Subscription
from breathecode.utils import getLogger

logger = getLogger(__name__)


def calculate_renew_delta(subscription: Subscription):
    delta_args = {}
    if subscription.renew_every_unit == 'DAY':
        delta_args['days'] = subscription.renew_every

    elif subscription.renew_every_unit == 'WEEK':
        delta_args['weeks'] = subscription.renew_every

    elif subscription.renew_every_unit == 'MONTH':
        delta_args['months'] = subscription.renew_every

    elif subscription.renew_every_unit == 'YEAR':
        delta_args['years'] = subscription.renew_every

    return relativedelta(**delta_args)
