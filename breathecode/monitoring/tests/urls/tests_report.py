from datetime import date

from django.contrib.auth.models import User
from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.monitoring.reports.acquisition.models import AcquisitionReport
from breathecode.monitoring.reports.churn.models import ChurnAlert, ChurnRiskReport

from ..mixins import MonitoringTestCase


class MonitoringReportTestSuite(MonitoringTestCase):
    def test_without_auth(self):
        url = reverse_lazy("monitoring:report_types")
        response = self.client.get(url)

        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_without_academy_header(self):
        self.generate_models(authenticate=True, profile_academy=True, role=1, capability="read_monitoring_report")

        url = reverse_lazy("monitoring:report_types")
        response = self.client.get(url)

        json = response.json()
        expected = {
            "detail": "Missing academy_id parameter expected for the endpoint url or 'Academy' header",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_without_capability(self):
        self.headers(academy=1)
        self.generate_models(authenticate=True, profile_academy=True)

        url = reverse_lazy("monitoring:report_types")
        response = self.client.get(url)

        json = response.json()
        expected = {
            "detail": "You (user: 1) don't have this capability: read_monitoring_report for academy 1",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_report_types(self):
        self.headers(academy=1)
        self.generate_models(authenticate=True, profile_academy=True, role=1, capability="read_monitoring_report")

        url = reverse_lazy("monitoring:report_types")
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json), 2)
        self.assertEqual(set([x["slug"] for x in json]), {"churn", "acquisition"})
        self.assertEqual(set([x["supports_detail"] for x in json]), {True})
        self.assertEqual(set([x["supports_summary"] for x in json]), {True})

    def test_get_churn_report_list_scoped_to_latest_date_and_academy(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True, role=1, capability="read_monitoring_report")

        secondary_user = User.objects.create(username="secondary-user", email="secondary@4geeks.com")
        other_user = User.objects.create(username="other-user", email="other@4geeks.com")
        external_user = User.objects.create(username="external-user", email="external@4geeks.com")
        other_academy_model = self.generate_models(
            academy=1,
            city=1,
            country=1,
        )

        ChurnRiskReport.objects.create(
            user=secondary_user,
            academy=model.academy,
            report_date=date(2026, 4, 10),
            churn_risk_score=21.0,
            risk_level=ChurnRiskReport.RiskLevel.LOW,
        )
        ChurnRiskReport.objects.create(
            user=secondary_user,
            academy=model.academy,
            report_date=date(2026, 4, 11),
            churn_risk_score=55.0,
            risk_level=ChurnRiskReport.RiskLevel.HIGH,
        )
        ChurnRiskReport.objects.create(
            user=other_user,
            academy=model.academy,
            report_date=date(2026, 4, 11),
            churn_risk_score=82.0,
            risk_level=ChurnRiskReport.RiskLevel.CRITICAL,
        )
        ChurnRiskReport.objects.create(
            user=external_user,
            academy=other_academy_model.academy,
            report_date=date(2026, 4, 11),
            churn_risk_score=99.0,
            risk_level=ChurnRiskReport.RiskLevel.CRITICAL,
        )

        url = reverse_lazy("monitoring:report_type", kwargs={"report_type": "churn"})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json), 2)
        self.assertEqual(set([x["academy_id"] for x in json]), {model.academy.id})
        self.assertEqual(set([x["report_date"] for x in json]), {"2026-04-11"})

    def test_get_churn_report_detail(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True, role=1, capability="read_monitoring_report")

        secondary_user = User.objects.create(username="detail-user", email="detail@4geeks.com")
        report = ChurnRiskReport.objects.create(
            user=secondary_user,
            academy=model.academy,
            report_date=date(2026, 4, 11),
            churn_risk_score=67.0,
            risk_level=ChurnRiskReport.RiskLevel.HIGH,
            details={"source": "test"},
        )

        url = reverse_lazy(
            "monitoring:report_type_id",
            kwargs={"report_type": "churn", "report_id": report.id},
        )
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json["id"], report.id)
        self.assertEqual(json["details"], {"source": "test"})

    def test_get_churn_report_summary(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True, role=1, capability="read_monitoring_report")

        secondary_user = User.objects.create(username="summary-user", email="summary@4geeks.com")
        report = ChurnRiskReport.objects.create(
            user=secondary_user,
            academy=model.academy,
            report_date=date(2026, 4, 11),
            churn_risk_score=89.0,
            risk_level=ChurnRiskReport.RiskLevel.CRITICAL,
            has_payment_issues=True,
        )
        ChurnAlert.objects.create(
            user=secondary_user,
            academy=model.academy,
            alert_type=ChurnAlert.AlertType.PAYMENT_RISK,
            severity=ChurnAlert.Severity.CRITICAL,
            metrics_snapshot={"risk": report.churn_risk_score},
        )

        url = reverse_lazy("monitoring:report_type_summary", kwargs={"report_type": "churn"})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json["total"], 1)
        self.assertEqual(json["payment_risk_count"], 1)
        self.assertEqual(json["unresolved_alert_count"], 1)
        self.assertEqual(json["risk_levels"]["CRITICAL"], 1)

    def test_get_churn_report_with_invalid_report_type(self):
        self.headers(academy=1)
        self.generate_models(authenticate=True, profile_academy=True, role=1, capability="read_monitoring_report")

        url = reverse_lazy("monitoring:report_type", kwargs={"report_type": "unknown"})
        response = self.client.get(url)
        json = response.json()

        expected = {"detail": "report-type-not-found", "status_code": 404}

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(json, expected)

    def test_get_acquisition_report_list_scoped_to_latest_date_and_academy(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True, role=1, capability="read_monitoring_report")
        other_academy_model = self.generate_models(academy=1, city=1, country=1)

        AcquisitionReport.objects.create(
            source_type=AcquisitionReport.SourceType.USER_INVITE,
            source_id=101,
            report_date=date(2026, 4, 10),
            academy=model.academy,
            email="one@4geeks.com",
            funnel_tier=AcquisitionReport.FunnelTier.NURTURE_INVITE,
            team_seat_invite=False,
            details={"source": "test"},
        )
        AcquisitionReport.objects.create(
            source_type=AcquisitionReport.SourceType.USER_INVITE,
            source_id=102,
            report_date=date(2026, 4, 11),
            academy=model.academy,
            email="two@4geeks.com",
            funnel_tier=AcquisitionReport.FunnelTier.NURTURE_INVITE,
            asset_slug="asset-a",
            event_slug="workshop-a",
            team_seat_invite=False,
            details={"source": "test"},
        )
        AcquisitionReport.objects.create(
            source_type=AcquisitionReport.SourceType.FORM_ENTRY,
            source_id=103,
            report_date=date(2026, 4, 11),
            academy=model.academy,
            email="three@4geeks.com",
            funnel_tier=AcquisitionReport.FunnelTier.STRONG_LEAD,
            lead_type="STRONG",
            team_seat_invite=False,
            details={"source": "test"},
        )
        AcquisitionReport.objects.create(
            source_type=AcquisitionReport.SourceType.USER_INVITE,
            source_id=104,
            report_date=date(2026, 4, 11),
            academy=other_academy_model.academy,
            email="external@4geeks.com",
            funnel_tier=AcquisitionReport.FunnelTier.NURTURE_INVITE,
            team_seat_invite=False,
            details={"source": "test"},
        )

        url = reverse_lazy("monitoring:report_type", kwargs={"report_type": "acquisition"})
        response = self.client.get(url)
        payload = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(payload), 2)
        self.assertEqual(set([x["academy_id"] for x in payload]), {model.academy.id})
        self.assertEqual(set([x["report_date"] for x in payload]), {"2026-04-11"})

    def test_get_acquisition_report_detail(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True, role=1, capability="read_monitoring_report")

        report = AcquisitionReport.objects.create(
            source_type=AcquisitionReport.SourceType.USER_INVITE,
            source_id=105,
            report_date=date(2026, 4, 11),
            academy=model.academy,
            email="detail@4geeks.com",
            funnel_tier=AcquisitionReport.FunnelTier.NURTURE_INVITE,
            asset_slug="asset-d",
            event_slug="workshop-d",
            team_seat_invite=False,
            details={"conversion_info": {"utm_source": "an"}},
        )

        url = reverse_lazy(
            "monitoring:report_type_id",
            kwargs={"report_type": "acquisition", "report_id": report.id},
        )
        response = self.client.get(url)
        payload = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(payload["id"], report.id)
        self.assertEqual(payload["asset_slug"], "asset-d")
        self.assertEqual(payload["details"]["conversion_info"]["utm_source"], "an")

    def test_get_acquisition_report_summary(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True, role=1, capability="read_monitoring_report")

        AcquisitionReport.objects.create(
            source_type=AcquisitionReport.SourceType.USER_INVITE,
            source_id=106,
            report_date=date(2026, 4, 11),
            academy=model.academy,
            email="summary-1@4geeks.com",
            funnel_tier=AcquisitionReport.FunnelTier.NURTURE_INVITE,
            asset_slug="asset-summary",
            event_slug="workshop-summary",
            utm_source="an",
            utm_campaign="campaign-1",
            conversion_url="/workshops/summary",
            team_seat_invite=True,
            details={"source": "invite"},
        )
        AcquisitionReport.objects.create(
            source_type=AcquisitionReport.SourceType.FORM_ENTRY,
            source_id=107,
            report_date=date(2026, 4, 11),
            academy=model.academy,
            email="summary-2@4geeks.com",
            funnel_tier=AcquisitionReport.FunnelTier.WON_OR_SALE,
            deal_status="WON",
            team_seat_invite=False,
            details={"source": "form"},
        )

        url = reverse_lazy("monitoring:report_type_summary", kwargs={"report_type": "acquisition"})
        response = self.client.get(url)
        payload = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(payload["total"], 2)
        self.assertEqual(payload["by_funnel_tier"]["1"], 1)
        self.assertEqual(payload["by_funnel_tier"]["4"], 1)
        self.assertEqual(payload["by_funnel_tier_label"]["won_or_sale"], 1)
        self.assertEqual(payload["by_funnel_tier_label"]["nurture_invite"], 1)
        self.assertEqual(payload["team_seat_invite_count"], 1)
        self.assertEqual(payload["top_asset_slugs"][0]["asset_slug"], "asset-summary")
        self.assertEqual(payload["top_event_slugs"][0]["event_slug"], "workshop-summary")

    def test_get_acquisition_report_date_range(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True, role=1, capability="read_monitoring_report")

        AcquisitionReport.objects.create(
            source_type=AcquisitionReport.SourceType.USER_INVITE,
            source_id=108,
            report_date=date(2026, 4, 10),
            academy=model.academy,
            email="range-1@4geeks.com",
            funnel_tier=AcquisitionReport.FunnelTier.NURTURE_INVITE,
            team_seat_invite=False,
            details={},
        )
        AcquisitionReport.objects.create(
            source_type=AcquisitionReport.SourceType.USER_INVITE,
            source_id=109,
            report_date=date(2026, 4, 11),
            academy=model.academy,
            email="range-2@4geeks.com",
            funnel_tier=AcquisitionReport.FunnelTier.NURTURE_INVITE,
            team_seat_invite=False,
            details={},
        )
        AcquisitionReport.objects.create(
            source_type=AcquisitionReport.SourceType.USER_INVITE,
            source_id=110,
            report_date=date(2026, 4, 12),
            academy=model.academy,
            email="range-3@4geeks.com",
            funnel_tier=AcquisitionReport.FunnelTier.NURTURE_INVITE,
            team_seat_invite=False,
            details={},
        )

        url = reverse_lazy("monitoring:report_type", kwargs={"report_type": "acquisition"})
        response = self.client.get(url, data={"date_start": "2026-04-10", "date_end": "2026-04-11"})
        payload = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(payload), 2)
        self.assertEqual(set([x["report_date"] for x in payload]), {"2026-04-10", "2026-04-11"})
