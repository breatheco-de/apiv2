from datetime import timedelta
from django.core.management.base import BaseCommand

from breathecode.payments.actions import payWithStripe
from ...models import ServiceCreditItem, Subscription, Credit
from django.utils import timezone
from breathecode.notify import actions as notify_actions

from dateutil.relativedelta import relativedelta


# renew the subscriptions every 1 hours
class Command(BaseCommand):
    help = 'Renew credits'

    def handle(self, *args, **options):
        utc_now = timezone.now()
        subscriptions = Subscription.objects.filter(
            valid_until__lte=utc_now, renew_credits_at__lte=utc_now +
            timedelta(hours=2)).exclude(status='CANCELLED').exclude(status='DEPRECATED')

        for subscription in subscriptions:
            try:
                invoice = payWithStripe()
            except Exception:
                subscription.status = 'PAYMENT_ISSUE'
                subscription.save()
                continue

            delta_args = {}
            if subscription.renew_every_unit == 'DAY':
                delta_args['days'] = subscription.renew_every

            elif subscription.renew_every_unit == 'WEEK':
                delta_args['weeks'] = subscription.renew_every

            elif subscription.renew_every_unit == 'MONTH':
                delta_args['months'] = subscription.renew_every

            elif subscription.renew_every_unit == 'YEAR':
                delta_args['years'] = subscription.renew_every

            subscription.last_renew = utc_now
            subscription.renew_credits_at = utc_now + relativedelta(**delta_args)

            subscription.invoices.add(invoice)

            # for service in subscription.plan.services.all():
            credit = Credit()
            for service_item in subscription.services.all():
                new_service_credit = ServiceCreditItem(service=service_item.service,
                                                       unit_type=service_item.unit_type,
                                                       how_many=service_item.how_many)

                credit.services.add(new_service_credit)

            for plan in subscription.plans.all():
                for service_item in plan.services.all():
                    new_service_credit = ServiceCreditItem(service=service_item.service,
                                                           unit_type=service_item.unit_type,
                                                           how_many=service_item.how_many)

                    credit.services.add(new_service_credit)

            credit.invoice = invoice
            credit.valid_until = subscription.renew_credits_at
            credit.is_free_trial = False
            credit.save()

            subscription.save()

            data = {
                'SUBJECT':
                f'Your subscription has been renewed for {invoice.currency.format_value(invoice.amount)}',
                # 'LINK': f'https://assessment.breatheco.de/{user_assessment.id}?token={token.key}'
            }

            notify_actions.send_email_message('payment', invoice.user.email, data)
