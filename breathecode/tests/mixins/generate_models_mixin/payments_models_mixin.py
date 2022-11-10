"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.models_mixin import ModelsMixin

from .utils import create_models, get_list, is_valid, just_one


class PaymentsModelsMixin(ModelsMixin):

    def generate_payments_models(
            self,
            currency=False,
            #  price=False,
            service=False,
            service_item=False,
            plan=False,
            consumable=False,
            invoice=False,
            subscription=False,
            credit=False,
            payment_contact=False,
            financial_reputation=False,
            bag=False,
            models={},
            **kwargs):
        """Generate models"""
        models = models.copy()

        # if not 'currency' in models and (is_valid(currency) or is_valid(price) or is_valid(invoice)):
        if not 'currency' in models and (is_valid(currency) or is_valid(invoice) or is_valid(plan)
                                         or is_valid(service) or is_valid(service_item)):
            kargs = {}

            if 'country' in models:
                kargs['countries'] = get_list(models['country'])

            models['currency'] = create_models(currency, 'payments.Currency', **kargs)

            if 'academy' in models:
                for academy in (models['academy']
                                if isinstance(models['academy'], list) else [models['academy']]):
                    academy.main_currency = just_one(models['currency'])
                    academy.save()

        if not 'service' in models and (is_valid(service) or is_valid(service_item) or is_valid(consumable)):
            kargs = {}

            if 'currency' in models:
                kargs['currency'] = just_one(models['currency'])

            if 'academy' in models:
                kargs['owner'] = just_one(models['academy'])

            if 'group' in models:
                kargs['groups'] = get_list(models['group'])

            if 'cohort' in models:
                kargs['cohorts'] = get_list(models['cohort'])

            if 'mentorship_service' in models:
                kargs['mentorship_services'] = get_list(models['mentorship_service'])

            models['service'] = create_models(service, 'payments.Service', **kargs)

        if not 'service_item' in models and is_valid(service_item):
            kargs = {}

            if 'service' in models:
                kargs['service'] = just_one(models['service'])

            models['service_item'] = create_models(service_item, 'payments.ServiceItem', **kargs)

        if not 'plan' in models and is_valid(plan):
            kargs = {}

            # if 'price' in models:
            #     kargs['price'] = just_one(models['price'])

            if 'currency' in models:
                kargs['currency'] = just_one(models['currency'])

            if 'service_item' in models:
                kargs['services'] = get_list(models['service_item'])

            if 'academy' in models:
                kargs['owner'] = just_one(models['academy'])

            models['plan'] = create_models(plan, 'payments.Plan', **kargs)

        if not 'consumable' in models and is_valid(consumable):
            kargs = {}

            if 'service' in models:
                kargs['service'] = just_one(models['service'])

            if 'user' in models:
                kargs['user'] = just_one(models['user'])

            models['consumable'] = create_models(consumable, 'payments.Consumable', **kargs)

        if not 'invoice' in models and (is_valid(invoice) or is_valid(credit)):
            kargs = {}

            if 'currency' in models:
                kargs['currency'] = just_one(models['currency'])

            if 'user' in models:
                kargs['user'] = just_one(models['user'])

            if 'academy' in models:
                kargs['academy'] = just_one(models['academy'])

            models['invoice'] = create_models(invoice, 'payments.Invoice', **kargs)

        if not 'subscription' in models and is_valid(subscription):
            kargs = {}

            if 'invoice' in models:
                kargs['invoices'] = get_list(models['invoice'])

            if 'user' in models:
                kargs['user'] = just_one(models['user'])

            if 'service_item' in models:
                kargs['service'] = just_one(models['service_item'])

            if 'plan' in models:
                kargs['plan'] = just_one(models['plan'])

            models['subscription'] = create_models(subscription, 'payments.Subscription', **kargs)

        if not 'credit' in models and is_valid(credit):
            kargs = {}

            if 'consumable' in models:
                kargs['services'] = get_list(models['consumable'])

            if 'invoice' in models:
                kargs['invoice'] = just_one(models['invoice'])

            models['credit'] = create_models(credit, 'payments.Credit', **kargs)

        if not 'payment_contact' in models and is_valid(payment_contact):
            kargs = {}

            if 'user' in models:
                kargs['user'] = just_one(models['user'])

            models['payment_contact'] = create_models(payment_contact, 'payments.PaymentContact', **kargs)

        if not 'financial_reputation' in models and is_valid(financial_reputation):
            kargs = {}

            if 'user' in models:
                kargs['user'] = just_one(models['user'])

            models['financial_reputation'] = create_models(financial_reputation,
                                                           'payments.FinancialReputation', **kargs)

        if not 'bag' in models and is_valid(bag):
            kargs = {}

            if 'user' in models:
                kargs['user'] = just_one(models['user'])

            if 'academy' in models:
                kargs['academy'] = just_one(models['academy'])

            if 'currency' in models:
                kargs['currency'] = just_one(models['currency'])

            if 'service_item' in models:
                kargs['services'] = get_list(models['service_item'])

            if 'plan' in models:
                kargs['plans'] = get_list(models['plan'])

            models['bag'] = create_models(bag, 'payments.Bag', **kargs)

        return models
