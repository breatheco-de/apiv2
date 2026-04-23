from datetime import date

from django.contrib.auth.models import User
from django.urls.base import reverse_lazy
from rest_framework import status

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
        self.assertEqual(len(json), 1)
        self.assertEqual(json[0]["slug"], "churn")
        self.assertEqual(json[0]["supports_detail"], True)
        self.assertEqual(json[0]["supports_summary"], True)

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
