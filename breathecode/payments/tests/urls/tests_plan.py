import random
from unittest.mock import MagicMock, call, patch

from django.urls import reverse_lazy
from rest_framework import status
from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers

from breathecode.utils.api_view_extensions.extensions import lookup_extension
from ..mixins import PaymentsTestCase


def academy_serializer(academy):
    return {
        "id": academy.id,
        "name": academy.name,
        "slug": academy.slug,
    }


def service_item_serializer(service_item, service):
    return {
        "how_many": service_item.how_many,
        "service": {
            "groups": [],
            "private": service.private,
            "slug": service.slug,
            "title": service.title,
            "icon_url": service.icon_url,
        },
        "unit_type": service_item.unit_type,
        "sort_priority": service_item.sort_priority,
    }


def financing_option_serializer(financing_option, currency):
    return {
        "currency": {
            "code": currency.code,
            "name": currency.name,
        },
        "how_many_months": financing_option.how_many_months,
        "monthly_price": financing_option.monthly_price,
    }


def get_serializer(event, currency, service=None, academy=None, service_items=[], financing_options=[], cohorts=[]):
    if service_items:
        service_items = [service_item_serializer(x, service) for x in service_items]

    if financing_options:
        financing_options = [financing_option_serializer(x, currency) for x in financing_options]

    if academy:
        academy = academy_serializer(academy)

    return {
        "slug": event.slug,
        "currency": {
            "code": currency.code,
            "name": currency.name,
        },
        "financing_options": financing_options,
        "has_available_cohorts": len(cohorts) > 0,
        "has_waiting_list": event.has_waiting_list,
        "is_renewable": event.is_renewable,
        "owner": academy,
        "price_per_half": event.price_per_half,
        "price_per_month": event.price_per_month,
        "price_per_quarter": event.price_per_quarter,
        "price_per_year": event.price_per_year,
        "service_items": service_items,
        "slug": event.slug,
        "status": event.status,
        "time_of_life": event.time_of_life,
        "time_of_life_unit": event.time_of_life_unit,
        "trial_duration": event.trial_duration,
        "trial_duration_unit": event.trial_duration_unit,
    }


class SignalTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 GET without auth
    """

    # Given: 0 Plan
    # When: get with no auth
    # Then: return 200
    def test__no_auth(self):
        url = reverse_lazy("payments:plan")
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("payments.Plan"), [])

    # Given: 2 Plan, 4 PlanServiceItem, 2 ServiceItem and 1 Service
    # When: get with no auth and plan is renewable
    # Then: return 200 with 2 Plan with no financial options
    def test__two_items__plan_is_renewable(self):
        plan = {"time_of_life": None, "time_of_life_unit": None, "is_renewable": True}
        plan_service_items = [{"service_item_id": n, "plan_id": 1} for n in range(1, 3)] + [
            {"service_item_id": n, "plan_id": 2} for n in range(1, 3)
        ]
        model = self.bc.database.create(
            plan=(2, plan), service_item=2, plan_service_item=plan_service_items, financing_option=2
        )

        url = reverse_lazy("payments:plan")
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(
                model.plan[1], model.currency, model.service, service_items=model.service_item, financing_options=[]
            ),
            get_serializer(
                model.plan[0], model.currency, model.service, service_items=model.service_item, financing_options=[]
            ),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Plan"),
            self.bc.format.to_dict(model.plan),
        )

    # Given: 2 Plan, 4 PlanServiceItem, 2 ServiceItem and 1 Service
    # When: get with no auth and plan is not renewable
    # Then: return 200 with 2 Plan with financial options
    def test__two_items__plan_is_not_renewable(self):
        plan = {"time_of_life": 1, "time_of_life_unit": "WEEK", "is_renewable": False}
        plan_service_items = [{"service_item_id": n, "plan_id": 1} for n in range(1, 3)] + [
            {"service_item_id": n, "plan_id": 2} for n in range(1, 3)
        ]
        model = self.bc.database.create(
            plan=(2, plan), service_item=2, plan_service_item=plan_service_items, financing_option=2
        )

        url = reverse_lazy("payments:plan")
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(
                model.plan[1],
                model.currency,
                model.service,
                service_items=model.service_item,
                financing_options=model.financing_option,
            ),
            get_serializer(
                model.plan[0],
                model.currency,
                model.service,
                service_items=model.service_item,
                financing_options=model.financing_option,
            ),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Plan"),
            self.bc.format.to_dict(model.plan),
        )

    """
    🔽🔽🔽 With cohort
    """

    # Given: 2 Plan, 4 PlanServiceItem, 2 ServiceItem and 1 Service
    # When: get with no auth and cohort provided in the querystring
    # Then: return 400
    def test__cohort_not_found(self):
        plan = {"time_of_life": None, "time_of_life_unit": None, "is_renewable": True}
        plan_service_items = [{"service_item_id": n, "plan_id": 1} for n in range(1, 3)] + [
            {"service_item_id": n, "plan_id": 2} for n in range(1, 3)
        ]
        model = self.bc.database.create(
            plan=(2, plan), service_item=2, plan_service_item=plan_service_items, financing_option=2
        )

        url = reverse_lazy("payments:plan") + "?cohort=1"
        response = self.client.get(url)

        json = response.json()
        expected = {"detail": "cohort-not-found", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.bc.database.list_of("payments.Plan"),
            self.bc.format.to_dict(model.plan),
        )

    # Given: 2 Plan, 4 PlanServiceItem, 2 ServiceItem, 1 Service,
    #     -> 1 Cohort, 1 SyllabusVersion and 1 Academy
    # When: get with no auth and cohort provided in the querystring,
    #    -> plan is_onboarding is False
    # Then: return 200 with 2 Plan with no financial options
    def test__cohort_exists__is_onboarding_is_false(self):
        plan = {"time_of_life": None, "time_of_life_unit": None, "is_renewable": True, "is_onboarding": False}
        plan_service_items = [{"service_item_id": n, "plan_id": 1} for n in range(1, 3)] + [
            {"service_item_id": n, "plan_id": 2} for n in range(1, 3)
        ]
        cohort = {"available_as_saas": True}
        model = self.bc.database.create(
            plan=(2, plan),
            service_item=2,
            plan_service_item=plan_service_items,
            financing_option=2,
            cohort=cohort,
            syllabus_version=1,
        )

        url = reverse_lazy("payments:plan") + "?cohort=1"
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Plan"),
            self.bc.format.to_dict(model.plan),
        )

    # Given: 2 Plan, 4 PlanServiceItem, 2 ServiceItem, 1 Service,
    #     -> 1 Cohort and 1 Academy
    # When: get with no auth and cohort provided in the querystring,
    #    -> plan is_onboarding is True
    # Then: return 200 with 2 Plan with no financial options
    def test__cohort_exists__is_onboarding_is_true(self):
        plan = {"time_of_life": None, "time_of_life_unit": None, "is_renewable": True, "is_onboarding": True}
        plan_service_items = [{"service_item_id": n, "plan_id": 1} for n in range(1, 3)] + [
            {"service_item_id": n, "plan_id": 2} for n in range(1, 3)
        ]
        model = self.bc.database.create(
            plan=(2, plan), service_item=2, plan_service_item=plan_service_items, financing_option=2, cohort=1
        )

        url = reverse_lazy("payments:plan") + "?cohort=1"
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Plan"),
            self.bc.format.to_dict(model.plan),
        )

    # Given: 2 Plan, 4 PlanServiceItem, 2 ServiceItem, 1 Service,
    #     -> 1 Cohort, 1 SyllabusVersion and 1 Academy
    # When: get with no auth and cohort provided in the querystring,
    #    -> plan is_onboarding is True
    # Then: return 200 with 2 Plan with no financial options
    def test__cohort_exists__is_onboarding_is_true(self):
        plan = {"time_of_life": None, "time_of_life_unit": None, "is_renewable": True, "is_onboarding": True}
        plan_service_items = [{"service_item_id": n, "plan_id": 1} for n in range(1, 3)] + [
            {"service_item_id": n, "plan_id": 2} for n in range(1, 3)
        ]
        cohort = {"available_as_saas": True}
        academy = {"available_as_saas": True}
        model = self.bc.database.create(
            plan=(2, plan),
            service_item=2,
            plan_service_item=plan_service_items,
            financing_option=2,
            cohort=cohort,
            cohort_set=1,
            cohort_set_cohort=1,
            syllabus_version=1,
            academy=academy,
        )

        url = reverse_lazy("payments:plan") + "?cohort=1"
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(
                model.plan[1],
                model.currency,
                model.service,
                model.academy,
                service_items=model.service_item,
                cohorts=[model.cohort],
                financing_options=[],
            ),
            get_serializer(
                model.plan[0],
                model.currency,
                model.service,
                model.academy,
                service_items=model.service_item,
                cohorts=[model.cohort],
                financing_options=[],
            ),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Plan"),
            self.bc.format.to_dict(model.plan),
        )

    """
    🔽🔽🔽 With cohort
    """

    # Given: 2 Plan, 4 PlanServiceItem, 2 ServiceItem and 1 Service
    # When: get with no auth and cohort provided in the querystring
    # Then: return 400
    def test__syllabus_not_found(self):
        plan = {"time_of_life": None, "time_of_life_unit": None, "is_renewable": True}
        plan_service_items = [{"service_item_id": n, "plan_id": 1} for n in range(1, 3)] + [
            {"service_item_id": n, "plan_id": 2} for n in range(1, 3)
        ]
        model = self.bc.database.create(
            plan=(2, plan), service_item=2, plan_service_item=plan_service_items, financing_option=2
        )

        url = reverse_lazy("payments:plan") + "?syllabus=1"
        response = self.client.get(url)

        json = response.json()
        expected = {"detail": "syllabus-not-found", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.bc.database.list_of("payments.Plan"),
            self.bc.format.to_dict(model.plan),
        )

    # Given: 2 Plan, 4 PlanServiceItem, 2 ServiceItem, 1 Service,
    #     -> 1 Cohort, 1 SyllabusVersion and 1 Academy
    # When: get with no auth and cohort provided in the querystring,
    #    -> plan is_onboarding is False
    # Then: return 200 with 2 Plan with no financial options
    def test__syllabus_exists__is_onboarding_is_false(self):
        plan = {"time_of_life": None, "time_of_life_unit": None, "is_renewable": True, "is_onboarding": False}
        plan_service_items = [{"service_item_id": n, "plan_id": 1} for n in range(1, 3)] + [
            {"service_item_id": n, "plan_id": 2} for n in range(1, 3)
        ]
        cohort = {"available_as_saas": True}
        model = self.bc.database.create(
            plan=(2, plan),
            service_item=2,
            plan_service_item=plan_service_items,
            financing_option=2,
            cohort=cohort,
            syllabus_version=1,
        )

        url = reverse_lazy("payments:plan") + "?syllabus=1"
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Plan"),
            self.bc.format.to_dict(model.plan),
        )

    # Given: 2 Plan, 4 PlanServiceItem, 2 ServiceItem, 1 Service,
    #     -> 1 Cohort and 1 Academy
    # When: get with no auth and cohort provided in the querystring,
    #    -> plan is_onboarding is True
    # Then: return 200 with 2 Plan with no financial options
    def test__syllabus_exists__is_onboarding_is_true(self):
        plan = {"time_of_life": None, "time_of_life_unit": None, "is_renewable": True, "is_onboarding": True}
        plan_service_items = [{"service_item_id": n, "plan_id": 1} for n in range(1, 3)] + [
            {"service_item_id": n, "plan_id": 2} for n in range(1, 3)
        ]
        model = self.bc.database.create(
            plan=(2, plan), service_item=2, plan_service_item=plan_service_items, financing_option=2, cohort=1
        )

        url = reverse_lazy("payments:plan") + "?syllabus=1"
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Plan"),
            self.bc.format.to_dict(model.plan),
        )

    # Given: 2 Plan, 4 PlanServiceItem, 2 ServiceItem, 1 Service,
    #     -> 1 Cohort, 1 SyllabusVersion and 1 Academy
    # When: get with no auth and cohort provided in the querystring,
    #    -> plan is_onboarding is True
    # Then: return 200 with 2 Plan with no financial options
    def test__syllabus_exists__is_onboarding_is_true(self):
        plan = {"time_of_life": None, "time_of_life_unit": None, "is_renewable": True, "is_onboarding": True}
        plan_service_items = [{"service_item_id": n, "plan_id": 1} for n in range(1, 3)] + [
            {"service_item_id": n, "plan_id": 2} for n in range(1, 3)
        ]
        cohort = {"available_as_saas": True}
        academy = {"available_as_saas": True}
        model = self.bc.database.create(
            plan=(2, plan),
            service_item=2,
            plan_service_item=plan_service_items,
            financing_option=2,
            cohort=cohort,
            cohort_set=1,
            cohort_set_cohort=1,
            syllabus_version=1,
            academy=academy,
        )

        url = reverse_lazy("payments:plan") + "?syllabus=1"
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(
                model.plan[1],
                model.currency,
                model.service,
                model.academy,
                service_items=model.service_item,
                cohorts=[model.cohort],
                financing_options=[],
            ),
            get_serializer(
                model.plan[0],
                model.currency,
                model.service,
                model.academy,
                service_items=model.service_item,
                cohorts=[model.cohort],
                financing_options=[],
            ),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Plan"),
            self.bc.format.to_dict(model.plan),
        )

    """
    🔽🔽🔽 Lookup extension
    """

    # Given: compile_lookup was mocked
    # When: the mock is called
    # Then: the mock should be called with the correct arguments and does not raise an exception
    @patch(
        "breathecode.utils.api_view_extensions.extensions.lookup_extension.compile_lookup",
        MagicMock(wraps=lookup_extension.compile_lookup),
    )
    def test_lookup_extension(self):
        self.bc.request.set_headers(academy=1)

        plan = {"time_of_life": None, "time_of_life_unit": None}
        plan_service_items = [{"service_item_id": n, "plan_id": 1} for n in range(1, 3)] + [
            {"service_item_id": n, "plan_id": 2} for n in range(1, 3)
        ]
        model = self.bc.database.create(plan=(2, plan), service_item=2, plan_service_item=plan_service_items)

        args, kwargs = self.bc.format.call(
            "en",
            strings={
                "exact": [
                    "service_items__service__slug",
                ],
            },
            overwrite={
                "service_slug": "service_items__service__slug",
            },
            custom_fields={"is_onboarding": lambda: "true" if random.randint(0, 1) else "false"},
        )

        query = self.bc.format.lookup(*args, **kwargs)
        url = reverse_lazy("payments:plan") + "?" + self.bc.format.querystring(query)

        self.assertEqual([x for x in query], ["service_slug", "is_onboarding"])

        response = self.client.get(url)

        json = response.json()
        expected = []

        for x in ["overwrite", "custom_fields"]:
            if x in kwargs:
                del kwargs[x]

        for field in ["ids", "slugs"]:
            values = kwargs.get(field, tuple())
            kwargs[field] = tuple(values)

        for field in ["ints", "strings", "bools", "datetimes"]:
            modes = kwargs.get(field, {})
            for mode in modes:
                if not isinstance(kwargs[field][mode], tuple):
                    kwargs[field][mode] = tuple(kwargs[field][mode])

            kwargs[field] = frozenset(modes.items())

        self.bc.check.calls(
            lookup_extension.compile_lookup.call_args_list,
            [
                call(**kwargs),
            ],
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.Plan"),
            self.bc.format.to_dict(model.plan),
        )

    # When: get is called
    # Then: it's setup properly
    @patch.object(APIViewExtensionHandlers, "_spy_extensions", MagicMock())
    @patch.object(APIViewExtensionHandlers, "_spy_extension_arguments", MagicMock())
    def test_get__spy_extensions(self):
        """Test /cohort/:id without auth"""
        plan = {"time_of_life": None, "time_of_life_unit": None, "is_renewable": True}
        plan_service_items = [{"service_item_id": n, "plan_id": 1} for n in range(1, 3)]
        model = self.bc.database.create(
            plan=plan, service_item=2, plan_service_item=plan_service_items, financing_option=2
        )

        url = reverse_lazy("payments:plan")
        self.client.get(url)

        self.bc.check.calls(
            APIViewExtensionHandlers._spy_extensions.call_args_list,
            [
                call(["LanguageExtension", "LookupExtension", "PaginationExtension", "SortExtension"]),
            ],
        )

        self.bc.check.calls(
            APIViewExtensionHandlers._spy_extension_arguments.call_args_list,
            [
                call(sort="-id", paginate=True),
            ],
        )
