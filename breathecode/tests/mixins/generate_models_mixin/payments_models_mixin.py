"""
Collections of mixins used to login in authorize microservice
"""

from breathecode.admissions.models import Academy
from breathecode.tests.mixins.models_mixin import ModelsMixin

from .utils import create_models, get_list, is_valid, just_one


class PaymentsModelsMixin(ModelsMixin):

    def generate_payments_models(
        self,
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
        academy_service=False,
        academy=False,
        bag=False,
        cohort_set_cohort=False,
        plan_service_item_handler=False,
        mentorship_service_set=False,
        mentorship_service_set_translation=False,
        event_type_set=False,
        event_type_set_translation=False,
        subscription_service_item=False,
        plan_service_item=False,
        plan_financing=False,
        service_item_feature=False,
        financing_option=False,
        consumption_session=False,
        plan_offer=False,
        plan_offer_translation=False,
        provisioning_price=False,
        cohort_set=False,
        cohort_set_translation=False,
        service_set=False,
        service_set_translation=False,
        seller=False,
        coupon=False,
        models={},
        **kwargs
    ):
        """Generate models"""
        models = models.copy()

        if not "currency" in models and (
            is_valid(currency)
            or is_valid(invoice)
            or is_valid(plan)
            or is_valid(service)
            or is_valid(service_item)
            or is_valid(financing_option)
            or is_valid(academy_service)
            or is_valid(provisioning_price)
        ):
            kargs = {}

            if "country" in models:
                kargs["countries"] = get_list(models["country"])

            models["currency"] = create_models(currency, "payments.Currency", **kargs)

            if "academy" in models:
                academies_intances = models["academy"] if isinstance(models["academy"], list) else [models["academy"]]

                academies_arguments = academy if isinstance(academy, list) else [academy]

                size = len(academies_intances)
                for index in range(size):
                    academy_argument = academies_arguments[index] or {}
                    academy_instance = academies_intances[index]

                    if isinstance(academy_argument, Academy) and academy_argument.main_currency is None:
                        academy_argument.main_currency = just_one(models["currency"])
                        academy_argument.save()

                    elif isinstance(academy_argument, Academy) is False and (
                        isinstance(academy_argument, int)
                        or "main_currency" not in academy_argument
                        or academy_argument["main_currency"] is not None
                    ):
                        academy_instance.main_currency = just_one(models["currency"])
                        academy_instance.save()

        if not "service" in models and (
            is_valid(service)
            or is_valid(service_item)
            or is_valid(consumable)
            or is_valid(service_translation)
            or is_valid(academy_service)
        ):
            kargs = {}

            if "currency" in models:
                kargs["currency"] = just_one(models["currency"])

            if "academy" in models:
                kargs["owner"] = just_one(models["academy"])

            if "group" in models:
                kargs["groups"] = get_list(models["group"])

            models["service"] = create_models(service, "payments.Service", **kargs)

        if not "service_translation" in models and is_valid(service_translation):
            kargs = {}

            if "service" in models:
                kargs["service"] = just_one(models["service"])

            models["service_translation"] = create_models(service_translation, "payments.ServiceTranslation", **kargs)

        if not "service_item" in models and (
            is_valid(service_item)
            or is_valid(consumable)
            or is_valid(service_stock_scheduler)
            or is_valid(subscription_service_item)
            or is_valid(plan_service_item)
            or is_valid(service_item_feature)
        ):
            kargs = {}

            if "service" in models:
                kargs["service"] = just_one(models["service"])

            models["service_item"] = create_models(service_item, "payments.ServiceItem", **kargs)

        if not "service_item_feature" in models and is_valid(service_item_feature):
            kargs = {}

            if "service_item" in models:
                kargs["service_item"] = just_one(models["service_item"])

            models["service_item_feature"] = create_models(service_item_feature, "payments.ServiceItemFeature", **kargs)

        if not "financing_option" in models and is_valid(financing_option):
            kargs = {}

            if "currency" in models:
                kargs["currency"] = just_one(models["currency"])

            models["financing_option"] = create_models(financing_option, "payments.FinancingOption", **kargs)

        if not "cohort_set" in models and (is_valid(cohort_set) or is_valid(cohort_set_translation)):
            kargs = {}

            if "academy" in models:
                kargs["academy"] = just_one(models["academy"])

            models["cohort_set"] = create_models(cohort_set, "payments.CohortSet", **kargs)

        if not "cohort_set_cohort" in models and is_valid(cohort_set_cohort):
            kargs = {}

            if "cohort_set" in models:
                kargs["cohort_set"] = just_one(models["cohort_set"])

            if "cohort" in models:
                kargs["cohort"] = just_one(models["cohort"])

            models["cohort_set_cohort"] = create_models(cohort_set_cohort, "payments.CohortSetCohort", **kargs)

        if not "cohort_set_translation" in models and is_valid(cohort_set_translation):
            kargs = {}

            if "cohort_set" in models:
                kargs["cohort_set"] = get_list(models["cohort_set"])

            models["cohort_set_translation"] = create_models(
                mentorship_service_set_translation, "payments.CohortSetTranslation", **kargs
            )

        if not "mentorship_service_set" in models and (
            is_valid(mentorship_service_set) or is_valid(mentorship_service_set_translation)
        ):
            kargs = {}

            if "mentorship_service" in models:
                kargs["mentorship_services"] = get_list(models["mentorship_service"])

            if "academy" in models:
                kargs["academy"] = just_one(models["academy"])

            models["mentorship_service_set"] = create_models(
                mentorship_service_set, "payments.MentorshipServiceSet", **kargs
            )

        if not "mentorship_service_set_translation" in models and is_valid(mentorship_service_set_translation):
            kargs = {}

            if "mentorship_service_set" in models:
                kargs["mentorship_service_set"] = get_list(models["mentorship_service_set"])

            if "academy" in models:
                kargs["academy"] = just_one(models["academy"])

            models["mentorship_service_set_translation"] = create_models(
                mentorship_service_set_translation, "payments.MentorshipServiceSetTranslation", **kargs
            )

        if not "event_type_set" in models and (is_valid(event_type_set) or is_valid(event_type_set_translation)):
            kargs = {}

            if "event_type" in models:
                kargs["event_types"] = get_list(models["event_type"])

            if "academy" in models:
                kargs["academy"] = just_one(models["academy"])

            models["event_type_set"] = create_models(event_type_set, "payments.EventTypeSet", **kargs)

        if not "event_type_set_translation" in models and is_valid(event_type_set_translation):
            kargs = {}

            if "event_type_sets" in models:
                kargs["event_type_sets"] = get_list(models["event_type_set"])

            if "academy" in models:
                kargs["academy"] = just_one(models["academy"])

            models["event_type_set_translation"] = create_models(
                event_type_set_translation, "payments.EventTypeSetTranslation", **kargs
            )

        if not "academy_service" in models and is_valid(academy_service):
            kargs = {}

            if "service" in models:
                kargs["service"] = just_one(models["service"])

            if "academy" in models:
                kargs["academy"] = just_one(models["academy"])

            if "currency" in models:
                kargs["currency"] = just_one(models["currency"])

            if "mentorship_service_set" in models:
                kargs["available_mentorship_service_sets"] = get_list(models["mentorship_service_set"])

            if "event_type_set" in models:
                kargs["available_event_type_sets"] = get_list(models["event_type_set"])

            models["academy_service"] = create_models(academy_service, "payments.AcademyService", **kargs)

        if not "plan" in models and (
            is_valid(plan) or is_valid(plan_translation) or is_valid(plan_service_item) or is_valid(plan_offer)
        ):
            kargs = {}

            if "currency" in models:
                kargs["currency"] = just_one(models["currency"])

            if "payment_service_scheduler" in models:
                kargs["schedulers"] = get_list(models["payment_service_scheduler"])

            if "financing_option" in models:
                kargs["financing_options"] = get_list(models["financing_option"])

            if "academy" in models:
                kargs["owner"] = just_one(models["academy"])

            if "mentorship_service_set" in models:
                kargs["mentorship_service_set"] = just_one(models["mentorship_service_set"])

            if "event_type_set" in models:
                kargs["event_type_set"] = just_one(models["event_type_set"])

            if "cohort_set" in models:
                kargs["cohort_set"] = just_one(models["cohort_set"])

            if "user_invite" in models:
                kargs["invites"] = get_list(models["user_invite"])

            models["plan"] = create_models(plan, "payments.Plan", **kargs)

        if not "plan_translation" in models and is_valid(plan_translation):
            kargs = {}

            if "plan" in models:
                kargs["plan"] = just_one(models["plan"])

            models["plan_translation"] = create_models(plan_translation, "payments.PlanTranslation", **kargs)

        if not "plan_offer" in models and (is_valid(plan_offer) or is_valid(plan_offer_translation)):
            kargs = {}

            if "plan" in models:
                kargs["original_plan"] = just_one(models["plan"])

            if "plan" in models:
                kargs["suggested_plan"] = just_one(models["plan"])

            models["plan_offer"] = create_models(plan_offer, "payments.PlanOffer", **kargs)

        if not "plan_offer_translation" in models and is_valid(plan_offer_translation):
            kargs = {}

            if "plan_offer" in models:
                kargs["offer"] = just_one(models["plan_offer"])

            models["plan_offer_translation"] = create_models(
                plan_offer_translation, "payments.PlanOfferTranslation", **kargs
            )

        if not "seller" in models and is_valid(seller):
            kargs = {}

            if "user" in models:
                kargs["user"] = just_one(models["user"])

            models["seller"] = create_models(seller, "payments.Seller", **kargs)

        if not "coupon" in models and is_valid(coupon):
            kargs = {}

            if "seller" in models:
                kargs["seller"] = just_one(models["seller"])

            if "plan" in models:
                kargs["plans"] = get_list(models["plan"])

            models["coupon"] = create_models(coupon, "payments.Coupon", **kargs)

        if not "bag" in models and (is_valid(bag) or is_valid(invoice)):
            kargs = {}

            if "academy" in models:
                kargs["academy"] = just_one(models["academy"])

            if "user" in models:
                kargs["user"] = just_one(models["user"])

            if "currency" in models:
                kargs["currency"] = just_one(models["currency"])

            if "service_item" in models:
                kargs["service_items"] = get_list(models["service_item"])

            if "plan" in models:
                kargs["plans"] = get_list(models["plan"])

            if "coupon" in models:
                kargs["coupons"] = get_list(models["coupon"])

            models["bag"] = create_models(bag, "payments.Bag", **kargs)

        if not "invoice" in models and is_valid(invoice):
            kargs = {}

            if "currency" in models:
                kargs["currency"] = just_one(models["currency"])

            if "bag" in models:
                kargs["bag"] = just_one(models["bag"])

            if "user" in models:
                kargs["user"] = just_one(models["user"])

            if "academy" in models:
                kargs["academy"] = just_one(models["academy"])

            models["invoice"] = create_models(invoice, "payments.Invoice", **kargs)

        if not "plan_financing" in models and is_valid(plan_financing):
            kargs = {}

            if "invoice" in models:
                kargs["invoices"] = get_list(models["invoice"])

            if "user" in models:
                kargs["user"] = just_one(models["user"])

            if "cohort_set" in models:
                kargs["selected_cohort_set"] = just_one(models["cohort_set"])

            if "cohort" in models:
                kargs["joined_cohorts"] = get_list(models["cohort"])

            if "mentorship_service_set" in models:
                kargs["selected_mentorship_service_set"] = just_one(models["mentorship_service_set"])

            if "event_type_set" in models:
                kargs["selected_event_type_set"] = just_one(models["event_type_set"])

            if "academy" in models:
                kargs["academy"] = just_one(models["academy"])

            if "plan" in models:
                kargs["plans"] = get_list(models["plan"])

            models["plan_financing"] = create_models(plan_financing, "payments.PlanFinancing", **kargs)

        if not "subscription" in models and (is_valid(subscription) or is_valid(subscription_service_item)):
            kargs = {}

            if "invoice" in models:
                kargs["invoices"] = get_list(models["invoice"])

            if "user" in models:
                kargs["user"] = just_one(models["user"])

            if "cohort_set" in models:
                kargs["selected_cohort_set"] = just_one(models["cohort_set"])

            if "cohort" in models:
                kargs["joined_cohorts"] = get_list(models["cohort"])

            if "mentorship_service_set" in models:
                kargs["selected_mentorship_service_set"] = just_one(models["mentorship_service_set"])

            if "event_type_set" in models:
                kargs["selected_event_type_set"] = just_one(models["event_type_set"])

            if "academy" in models:
                kargs["academy"] = just_one(models["academy"])

            if "plan" in models:
                kargs["plans"] = get_list(models["plan"])

            models["subscription"] = create_models(subscription, "payments.Subscription", **kargs)

        if not "subscription_service_item" in models and is_valid(subscription_service_item):
            kargs = {}

            if "subscription" in models:
                kargs["subscription"] = just_one(models["subscription"])

            if "service_item" in models:
                kargs["service_item"] = just_one(models["service_item"])

            if "mentorship_service_set" in models:
                kargs["mentorship_service_set"] = just_one(models["mentorship_service_set"])

            if "cohort_set" in models:
                kargs["cohort_sets"] = get_list(models["cohort_set"])

            models["subscription_service_item"] = create_models(
                subscription_service_item, "payments.SubscriptionServiceItem", **kargs
            )

        if not "consumable" in models and (is_valid(consumable) or is_valid(consumption_session)):
            kargs = {}

            if "service_item" in models:
                kargs["service_item"] = just_one(models["service_item"])

            if "user" in models:
                kargs["user"] = just_one(models["user"])

            if "cohort_set" in models:
                kargs["cohort_set"] = just_one(models["cohort_set"])

            if "mentorship_service_set" in models:
                kargs["mentorship_service_set"] = just_one(models["mentorship_service_set"])

            if "event_type_set" in models:
                kargs["event_type_set"] = just_one(models["event_type_set"])

            models["consumable"] = create_models(consumable, "payments.Consumable", **kargs)

        if not "consumption_session" in models and is_valid(consumption_session):
            kargs = {}

            if "consumable" in models:
                kargs["consumable"] = just_one(models["consumable"])

            if "user" in models:
                kargs["user"] = just_one(models["user"])

            models["consumption_session"] = create_models(consumption_session, "payments.ConsumptionSession", **kargs)

        if not "plan_service_item" in models and (is_valid(plan_service_item) or is_valid(plan_service_item_handler)):
            kargs = {}

            if "plan" in models:
                kargs["plan"] = just_one(models["plan"])

            if "service_item" in models:
                kargs["service_item"] = just_one(models["service_item"])

            models["plan_service_item"] = create_models(plan_service_item, "payments.PlanServiceItem", **kargs)

        if not "plan_service_item_handler" in models and is_valid(plan_service_item_handler):
            kargs = {}

            if "plan_service_item" in models:
                kargs["handler"] = just_one(models["plan_service_item"])

            if "subscription" in models:
                kargs["subscription"] = just_one(models["subscription"])

            if "plan_financing" in models:
                kargs["plan_financing"] = just_one(models["plan_financing"])

            models["plan_service_item_handler"] = create_models(
                plan_service_item_handler, "payments.PlanServiceItemHandler", **kargs
            )

        if not "service_stock_scheduler" in models and is_valid(service_stock_scheduler):
            kargs = {}

            if "subscription_service_item" in models:
                kargs["subscription_handler"] = just_one(models["subscription_service_item"])

            if "plan_service_item" in models:
                kargs["plan_handler"] = just_one(models["plan_service_item_handler"])

            if "consumable" in models:
                kargs["consumables"] = get_list(models["consumable"])

            models["service_stock_scheduler"] = create_models(
                service_stock_scheduler, "payments.ServiceStockScheduler", **kargs
            )

        if not "payment_contact" in models and is_valid(payment_contact):
            kargs = {}

            if "user" in models:
                kargs["user"] = just_one(models["user"])

            models["payment_contact"] = create_models(payment_contact, "payments.PaymentContact", **kargs)

        if not "financial_reputation" in models and is_valid(financial_reputation):
            kargs = {}

            if "user" in models:
                kargs["user"] = just_one(models["user"])

            models["financial_reputation"] = create_models(
                financial_reputation, "payments.FinancialReputation", **kargs
            )

        return models
