"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.models_mixin import ModelsMixin

from .utils import create_models, get_list, is_valid, just_one


class PaymentsModelsMixin(ModelsMixin):

    def generate_payments_models(self,
                                 currency=False,
                                 service=False,
                                 service_translation=False,
                                 service_item=False,
                                 plan=False,
                                 plan_translation=False,
                                 consumable=False,
                                 invoice=False,
                                 subscription=False,
                                 service_stock_scheduler=False,
                                 payment_contact=False,
                                 financial_reputation=False,
                                 academy=False,
                                 bag=False,
                                 plan_service_item_handler=False,
                                 mentorship_service_set=False,
                                 subscription_service_item=False,
                                 plan_service_item=False,
                                 plan_financing=False,
                                 service_item_feature=False,
                                 financing_option=False,
                                 consumption_session=False,
                                 plan_offer=False,
                                 plan_offer_translation=False,
                                 models={},
                                 **kwargs):
        """Generate models"""
        models = models.copy()

        if not 'currency' in models and (is_valid(currency) or is_valid(invoice) or is_valid(plan)
                                         or is_valid(service) or is_valid(service_item)
                                         or is_valid(financing_option)):
            kargs = {}

            if 'country' in models:
                kargs['countries'] = get_list(models['country'])

            models['currency'] = create_models(currency, 'payments.Currency', **kargs)

            if 'academy' in models:
                academies_intances = models['academy'] if isinstance(models['academy'],
                                                                     list) else [models['academy']]

                academies_arguments = academy if isinstance(academy, list) else [academy]

                size = len(academies_intances)
                for index in range(size):
                    academy_argument = academies_arguments[index] or {}
                    academy_instance = academies_intances[index]

                    if isinstance(academy_argument,
                                  int) or 'main_currency' not in academy_argument or academy_argument[
                                      'main_currency'] is not None:
                        academy_instance.main_currency = just_one(models['currency'])
                        academy_instance.save()

        if not 'service' in models and (is_valid(service) or is_valid(service_item) or is_valid(consumable)
                                        or is_valid(service_translation)):
            kargs = {}

            if 'currency' in models:
                kargs['currency'] = just_one(models['currency'])

            if 'academy' in models:
                kargs['owner'] = just_one(models['academy'])

            if 'group' in models:
                kargs['groups'] = get_list(models['group'])

            models['service'] = create_models(service, 'payments.Service', **kargs)

        if not 'service_translation' in models and is_valid(service_translation):
            kargs = {}

            if 'service' in models:
                kargs['service'] = just_one(models['service'])

            models['service_translation'] = create_models(service_translation, 'payments.ServiceTranslation',
                                                          **kargs)

        if not 'service_item' in models and (is_valid(service_item) or is_valid(consumable)
                                             or is_valid(service_stock_scheduler)
                                             or is_valid(subscription_service_item) or
                                             is_valid(plan_service_item) or is_valid(service_item_feature)):
            kargs = {}

            if 'service' in models:
                kargs['service'] = just_one(models['service'])

            models['service_item'] = create_models(service_item, 'payments.ServiceItem', **kargs)

        if not 'service_item_feature' in models and is_valid(service_item_feature):
            kargs = {}

            if 'service_item' in models:
                kargs['service_item'] = just_one(models['service_item'])

            models['service_item_feature'] = create_models(service_item_feature,
                                                           'payments.ServiceItemFeature', **kargs)

        if not 'financing_option' in models and is_valid(financing_option):
            kargs = {}

            if 'currency' in models:
                kargs['currency'] = just_one(models['currency'])

            models['financing_option'] = create_models(financing_option, 'payments.FinancingOption', **kargs)

        if not 'plan' in models and (is_valid(plan) or is_valid(plan_translation)
                                     or is_valid(plan_service_item) or is_valid(plan_offer)):
            kargs = {}

            # if 'price' in models:
            #     kargs['price'] = just_one(models['price'])

            if 'currency' in models:
                kargs['currency'] = just_one(models['currency'])

            # if 'service_item' in models:
            #     kargs['service_items'] = get_list(models['service_item'])

            if 'payment_service_scheduler' in models:
                kargs['schedulers'] = get_list(models['payment_service_scheduler'])

            if 'financing_option' in models:
                kargs['financing_options'] = get_list(models['financing_option'])

            if 'academy' in models:
                kargs['owner'] = just_one(models['academy'])

            models['plan'] = create_models(plan, 'payments.Plan', **kargs)

        if not 'plan_translation' in models and is_valid(plan_translation):
            kargs = {}

            if 'plan' in models:
                kargs['plan'] = just_one(models['plan'])

            models['plan_translation'] = create_models(plan_translation, 'payments.PlanTranslation', **kargs)

        if not 'plan_offer' in models and (is_valid(plan_translation) or is_valid(plan_offer_translation)):
            kargs = {}

            if 'plan' in models:
                kargs['original_plan'] = just_one(models['plan'])

            if 'syllabus' in models:
                kargs['from_syllabus'] = get_list(models['syllabus'])

            if 'plan' in models:
                kargs['suggested_plans'] = get_list(models['plan'])

            models['plan_offer'] = create_models(plan_offer, 'payments.PlanOffer', **kargs)

        if not 'plan_offer_translation' in models and is_valid(plan_offer_translation):
            kargs = {}

            if 'offer' in models:
                kargs['offer'] = just_one(models['plan_offer'])

            models['plan_offer_translation'] = create_models(plan_offer_translation,
                                                             'payments.PlanOfferTranslation', **kargs)

        if not 'bag' in models and (is_valid(bag) or is_valid(invoice)):
            kargs = {}

            if 'academy' in models:
                kargs['academy'] = just_one(models['academy'])

            if 'user' in models:
                kargs['user'] = just_one(models['user'])

            if 'currency' in models:
                kargs['currency'] = just_one(models['currency'])

            if 'service_item' in models:
                kargs['service_items'] = get_list(models['service_item'])

            if 'plan' in models:
                kargs['plans'] = get_list(models['plan'])

            models['bag'] = create_models(bag, 'payments.Bag', **kargs)

        if not 'invoice' in models and is_valid(invoice):
            kargs = {}

            if 'currency' in models:
                kargs['currency'] = just_one(models['currency'])

            if 'bag' in models:
                kargs['bag'] = just_one(models['bag'])

            if 'user' in models:
                kargs['user'] = just_one(models['user'])

            if 'academy' in models:
                kargs['academy'] = just_one(models['academy'])

            models['invoice'] = create_models(invoice, 'payments.Invoice', **kargs)

        if not 'subscription' in models and (is_valid(subscription) or is_valid(subscription_service_item)):
            kargs = {}

            if 'invoice' in models:
                kargs['invoices'] = get_list(models['invoice'])

            if 'user' in models:
                kargs['user'] = just_one(models['user'])

            if 'academy' in models:
                kargs['academy'] = just_one(models['academy'])

            # if 'service_item' in models:
            #     kargs['service_items'] = get_list(models['service_item'])

            if 'plan' in models:
                kargs['plans'] = get_list(models['plan'])

            models['subscription'] = create_models(subscription, 'payments.Subscription', **kargs)

        if not 'mentorship_service_set' in models and is_valid(mentorship_service_set):
            kargs = {}

            if 'mentorship_service' in models:
                kargs['mentorship_services'] = get_list(models['mentorship_service'])

            if 'academy' in models:
                kargs['academy'] = just_one(models['academy'])

            models['mentorship_service_set'] = create_models(mentorship_service_set,
                                                             'payments.MentorshipServiceSet', **kargs)

        if not 'subscription_service_item' in models and is_valid(subscription_service_item):
            kargs = {}

            if 'subscription' in models:
                kargs['subscription'] = just_one(models['subscription'])

            if 'service_item' in models:
                kargs['service_item'] = just_one(models['service_item'])

            if 'mentorship_service_set' in models:
                kargs['mentorship_service_set'] = just_one(models['mentorship_service_set'])

            if 'cohort' in models:
                kargs['cohorts'] = get_list(models['cohort'])

            models['subscription_service_item'] = create_models(subscription_service_item,
                                                                'payments.SubscriptionServiceItem', **kargs)

        if not 'plan_financing' in models and is_valid(plan_financing):
            kargs = {}

            if 'invoice' in models:
                kargs['invoices'] = get_list(models['invoice'])

            if 'user' in models:
                kargs['user'] = just_one(models['user'])

            if 'academy' in models:
                kargs['academy'] = just_one(models['academy'])

            if 'plan' in models:
                kargs['plans'] = get_list(models['plan'])

            models['plan_financing'] = create_models(plan_financing, 'payments.PlanFinancing', **kargs)

        if not 'consumable' in models and (is_valid(consumable) or is_valid(consumption_session)):
            kargs = {}

            if 'service_item' in models:
                kargs['service_item'] = just_one(models['service_item'])

            if 'user' in models:
                kargs['user'] = just_one(models['user'])

            if 'cohort' in models:
                kargs['cohort'] = just_one(models['cohort'])

            if 'mentorship_service' in models:
                kargs['mentorship_service'] = just_one(models['mentorship_service'])

            models['consumable'] = create_models(consumable, 'payments.Consumable', **kargs)

        if not 'consumption_session' in models and is_valid(consumption_session):
            kargs = {}

            if 'consumable' in models:
                kargs['consumable'] = just_one(models['consumable'])

            if 'user' in models:
                kargs['user'] = just_one(models['user'])

            models['consumption_session'] = create_models(consumption_session, 'payments.ConsumptionSession',
                                                          **kargs)

        if not 'plan_service_item' in models and (is_valid(plan_service_item)
                                                  or is_valid(plan_service_item_handler)):
            kargs = {}

            if 'plan' in models:
                kargs['plan'] = just_one(models['plan'])

            if 'service_item' in models:
                kargs['service_item'] = just_one(models['service_item'])

            if 'mentorship_service_set' in models:
                kargs['mentorship_service_set'] = just_one(models['mentorship_service_set'])

            if 'cohort' in models:
                kargs['cohorts'] = get_list(models['cohort'])

            models['plan_service_item'] = create_models(plan_service_item, 'payments.PlanServiceItem',
                                                        **kargs)

        if not 'plan_service_item_handler' in models and is_valid(plan_service_item_handler):
            kargs = {}

            if 'plan_service_item' in models:
                kargs['handler'] = just_one(models['plan_service_item'])

            if 'subscription' in models:
                kargs['subscription'] = just_one(models['subscription'])

            if 'plan_financing' in models:
                kargs['plan_financing'] = just_one(models['plan_financing'])

            models['plan_service_item_handler'] = create_models(plan_service_item_handler,
                                                                'payments.PlanServiceItemHandler', **kargs)

        if not 'service_stock_scheduler' in models and is_valid(service_stock_scheduler):
            kargs = {}

            if 'subscription_service_item' in models:
                kargs['subscription_handler'] = just_one(models['subscription_service_item'])

            if 'plan_service_item' in models:
                kargs['plan_handler'] = just_one(models['plan_service_item_handler'])

            if 'consumable' in models:
                kargs['consumables'] = get_list(models['consumable'])

            models['service_stock_scheduler'] = create_models(service_stock_scheduler,
                                                              'payments.ServiceStockScheduler', **kargs)

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

        return models
