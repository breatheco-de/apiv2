from breathecode.utils import Cache
from .models import PlanOffer, Subscription, PlanFinancing


class PlanOfferCache(Cache):
    model = PlanOffer


class SubscriptionCache(Cache):
    model = Subscription


class PlanFinancingCache(Cache):
    model = PlanFinancing
