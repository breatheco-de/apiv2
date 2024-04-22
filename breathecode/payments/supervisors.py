from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from breathecode.payments.models import ConsumptionSession
from breathecode.utils.decorators import supervisor

MIN_PENDING_SESSIONS = 30
MIN_CANCELLED_SESSIONS = 10


@supervisor(delta=timedelta(days=1))
def supervise_all_consumption_sessions():
    utc_now = timezone.now()

    done_sessions = ConsumptionSession.objects.filter(status='DONE',
                                                      eta__lte=utc_now,
                                                      eta__gte=utc_now - timedelta(days=1))
    pending_sessions = ConsumptionSession.objects.filter(status='PENDING',
                                                         eta__lte=utc_now,
                                                         eta__gte=utc_now - timedelta(days=1))

    done_amount = done_sessions.count()
    pending_amount = pending_sessions.count()

    if pending_amount and done_amount and (rate :=
                                           pending_amount / done_amount) >= 0.3 and done_amount > MIN_PENDING_SESSIONS:
        yield f'There has so much pending consumption sessions, {pending_amount} pending and rate {round(rate * 100, 2)}%'

    users = User.objects.filter(consumptionsession__status='CANCELLED',
                                consumptionsession__eta__lte=utc_now,
                                consumptionsession__eta__gte=utc_now - timedelta(days=1))

    for user in users:
        done_sessions = ConsumptionSession.objects.filter(user=user,
                                                          status='DONE',
                                                          operation_code='unsafe-consume-service-set',
                                                          consumable__service_set__isnull=False,
                                                          eta__lte=utc_now - timedelta(minutes=10))
        cancelled_sessions = ConsumptionSession.objects.filter(user=user,
                                                               status='CANCELLED',
                                                               operation_code='unsafe-consume-service-set',
                                                               consumable__service_set__isnull=False,
                                                               eta__lte=utc_now,
                                                               eta__gte=utc_now - timedelta(days=1))

        done_amount = done_sessions.count()
        cancelled_amount = cancelled_sessions.count()

        # this client should be a cheater
        if cancelled_amount and (rate :=
                                 cancelled_amount / done_amount) > 0.1 and done_amount >= MIN_CANCELLED_SESSIONS:
            yield f'There has {round(rate * 100, 2)}% cancelled consumption sessions, due to a bug or a cheater, user {user.email}'
