"""
Test /report/lead
"""

from datetime import datetime, timedelta, timezone as dt_timezone

from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

from breathecode.marketing.models import FormEntry

from ..mixins import MarketingTestCase


def set_created_at(form_entry, value):
    FormEntry.objects.filter(id=form_entry.id).update(created_at=value)


def utc(year, month, day, hour=12):
    return datetime(year, month, day, hour, tzinfo=dt_timezone.utc)


class LeadReportTestSuite(MarketingTestCase):
    """Test /report/lead"""

    def create_staff(self, form_entry=None, capability="read_lead", academy=1, **kwargs):
        model = self.bc.database.create(
            user=1,
            academy=academy,
            profile_academy=1,
            role=1,
            capability=capability,
            form_entry=form_entry,
            **kwargs,
        )
        self.client.force_authenticate(model.user)
        return model

    def get(self, query="", academy=1):
        if academy:
            self.bc.request.set_headers(academy=academy)

        url = reverse_lazy("marketing:report_lead") + query
        return self.client.get(url)

    """
    🔽🔽🔽 Auth
    """

    def test_without_auth(self):
        url = reverse_lazy("marketing:report_lead")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_with_academy_header__without_capability(self):
        model = self.bc.database.create(user=1, academy=1, profile_academy=1, role=1)
        self.client.force_authenticate(model.user)

        response = self.get("?by=course")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.json(),
            {"detail": "You (user: 1) don't have this capability: read_lead for academy 1", "status_code": 403},
        )

    def test_with_academy_header__scoped_to_that_academy(self):
        form_entries = [
            {"course": "full-stack", "academy_id": 1},
            {"course": "full-stack", "academy_id": 1},
            {"course": "full-stack", "academy_id": 2},
        ]
        self.create_staff(form_entry=form_entries, academy=2)

        response = self.get("?by=course")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [{"course": "full-stack", "total_leads": 2}])

    def test_without_academy_header__legacy_scoping(self):
        form_entries = [
            {"course": "full-stack", "academy_id": 1},
            {"course": "full-stack", "academy_id": 2},
        ]
        model = self.bc.database.create(user=1, academy=2, profile_academy=1, role=1, form_entry=form_entries)
        self.client.force_authenticate(model.user)

        response = self.get("?by=course", academy=None)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [{"course": "full-stack", "total_leads": 1}])

    def test_without_academy_header__academy_filters_location(self):
        form_entries = [
            {"course": "full-stack", "location": "downtown-miami"},
            {"course": "full-stack", "location": "madrid"},
        ]
        model = self.bc.database.create(user=1, academy=1, profile_academy=1, role=1, form_entry=form_entries)
        self.client.force_authenticate(model.user)

        response = self.get("?by=location&academy=madrid", academy=None)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [{"location": "madrid", "total_leads": 1}])

    """
    🔽🔽🔽 by allowlist
    """

    def test_by__rejects_fields_outside_the_allowlist(self):
        self.create_staff(form_entry=1)

        for field in ["email", "phone", "user__password", "academy__activecampaignacademy__ac_key", "id"]:
            response = self.get(f"?by={field}")

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.json(), {"detail": "invalid-group-by", "status_code": 400})

    def test_by__counts_leads_without_location(self):
        form_entries = [
            {"storage_status": "ERROR", "location": None},
            {"storage_status": "ERROR", "location": None},
            {"storage_status": "PERSISTED", "location": "downtown-miami"},
        ]
        self.create_staff(form_entry=form_entries)

        response = self.get("?by=storage_status")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            [
                {"storage_status": "ERROR", "total_leads": 2},
                {"storage_status": "PERSISTED", "total_leads": 1},
            ],
        )

    def test_by__default_group_by_with_created_date(self):
        model = self.create_staff(form_entry={"location": "downtown-miami", "course": "full-stack"})
        set_created_at(model.form_entry, utc(2026, 3, 2))

        response = self.get("?start=2026-03-01&end=2026-03-31")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            [
                {
                    "location": "downtown-miami",
                    "created_at__date": "2026-03-02",
                    "course": "full-stack",
                    "total_leads": 1,
                    "created_date": "20260302",
                }
            ],
        )

    """
    🔽🔽🔽 Filters
    """

    def test_filter__storage_status(self):
        form_entries = [
            {"storage_status": "ERROR", "course": "full-stack"},
            {"storage_status": "ERROR", "course": "data-science"},
            {"storage_status": "PERSISTED", "course": "full-stack"},
        ]
        self.create_staff(form_entry=form_entries)

        response = self.get("?by=course&storage_status=error")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            [
                {"course": "data-science", "total_leads": 1},
                {"course": "full-stack", "total_leads": 1},
            ],
        )

    def test_filter__invalid_choice_value(self):
        self.create_staff(form_entry=1)

        response = self.get("?by=course&storage_status=potato")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {"detail": "invalid-filter-value", "status_code": 400})

    def test_filter__utm_source(self):
        form_entries = [
            {"utm_source": "google", "course": "full-stack"},
            {"utm_source": "facebook", "course": "full-stack"},
        ]
        self.create_staff(form_entry=form_entries)

        response = self.get("?by=utm_source&utm_source=google")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [{"utm_source": "google", "total_leads": 1}])

    """
    🔽🔽🔽 Dates
    """

    def test_dates__end_is_inclusive(self):
        model = self.create_staff(form_entry={"course": "full-stack"})
        set_created_at(model.form_entry, utc(2026, 3, 10, hour=23))

        response = self.get("?by=course&start=2026-03-10&end=2026-03-10")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [{"course": "full-stack", "total_leads": 1}])

    def test_dates__invalid_format(self):
        self.create_staff()

        for query in ["?start=2026/03/01", "?end=yesterday"]:
            response = self.get(query)

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.json(), {"detail": "invalid-date-format", "status_code": 400})

    def test_dates__start_after_end(self):
        self.create_staff()

        response = self.get("?start=2026-03-10&end=2026-03-01")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {"detail": "invalid-date-range", "status_code": 400})

    def test_dates__range_too_long(self):
        self.create_staff()

        response = self.get("?start=2025-01-01&end=2026-03-01")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {"detail": "date-range-too-long", "status_code": 400})

    def test_dates__default_window_is_the_last_366_days(self):
        model = self.create_staff(form_entry=[{"course": "recent"}, {"course": "old"}])
        set_created_at(model.form_entry[1], timezone.now() - timedelta(days=400))

        response = self.get("?by=course")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [{"course": "recent", "total_leads": 1}])

    """
    🔽🔽🔽 Interval
    """

    def test_interval__week(self):
        model = self.create_staff(form_entry=3)
        set_created_at(model.form_entry[0], utc(2026, 3, 2))
        set_created_at(model.form_entry[1], utc(2026, 3, 4))
        set_created_at(model.form_entry[2], utc(2026, 3, 10))

        response = self.get("?by=created_at__date&interval=week&start=2026-03-01&end=2026-03-31")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            [
                {"period": "2026-03-02", "total_leads": 2},
                {"period": "2026-03-09", "total_leads": 1},
            ],
        )

    def test_interval__month(self):
        model = self.create_staff(form_entry=3)
        set_created_at(model.form_entry[0], utc(2026, 3, 2))
        set_created_at(model.form_entry[1], utc(2026, 3, 28))
        set_created_at(model.form_entry[2], utc(2026, 4, 3))

        response = self.get("?by=created_at__date&interval=month&start=2026-03-01&end=2026-04-30")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            [
                {"period": "2026-03-01", "total_leads": 2},
                {"period": "2026-04-01", "total_leads": 1},
            ],
        )

    def test_interval__invalid(self):
        self.create_staff()

        response = self.get("?interval=year")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {"detail": "invalid-interval", "status_code": 400})

    """
    🔽🔽🔽 Limit
    """

    def test_limit__truncates_rows(self):
        form_entries = [{"course": "a"}, {"course": "b"}, {"course": "c"}]
        self.create_staff(form_entry=form_entries)

        response = self.get("?by=course&limit=2")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [{"course": "a", "total_leads": 1}, {"course": "b", "total_leads": 1}])
        self.assertEqual(response["X-Total-Count"], "3")
        self.assertEqual(response["X-Truncated"], "true")

    def test_limit__not_truncated(self):
        self.create_staff(form_entry={"course": "a"})

        response = self.get("?by=course")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["X-Total-Count"], "1")
        self.assertEqual(response["X-Truncated"], "false")

    def test_limit__invalid(self):
        self.create_staff()

        for limit in ["0", "-1", "abc", "5001"]:
            response = self.get(f"?limit={limit}")

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.json(), {"detail": "invalid-limit", "status_code": 400})

    """
    🔽🔽🔽 Rate limit
    """

    def test_rate_limit__per_minute(self):
        self.create_staff()

        for _ in range(30):
            response = self.get("?by=course")
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.get("?by=course")

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(response["Retry-After"], "60")
        self.assertEqual(response.json(), {"detail": "rate-limit-exceeded", "status_code": 429})
