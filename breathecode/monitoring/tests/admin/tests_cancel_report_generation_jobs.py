from datetime import date
from django.http.request import HttpRequest
from unittest.mock import MagicMock

from ..mixins import MonitoringTestCase
from ...admin import ReportGenerationJobAdmin
from ...models import ReportGenerationJob


class ReportGenerationJobAdminActionTests(MonitoringTestCase):
    def _create_job(self, academy, status, parent=None, fingerprint="f-1"):
        return ReportGenerationJob.objects.create(
            report_type=ReportGenerationJob.ReportType.ACQUISITION,
            status=status,
            academy=academy,
            parent=parent,
            date_start=date(2026, 4, 1),
            date_end=date(2026, 4, 1),
            params={"date": "2026-04-01"},
            fingerprint=fingerprint,
        )

    def test_cancel_action_updates_pending_and_running(self):
        model = self.generate_models(academy=True)
        pending = self._create_job(model.academy, ReportGenerationJob.Status.PENDING, fingerprint="fp-p")
        running = self._create_job(model.academy, ReportGenerationJob.Status.RUNNING, fingerprint="fp-r")
        done = self._create_job(model.academy, ReportGenerationJob.Status.DONE, fingerprint="fp-d")

        request = HttpRequest()
        admin_instance = ReportGenerationJobAdmin(ReportGenerationJob, MagicMock())
        admin_instance.message_user = MagicMock()

        queryset = ReportGenerationJob.objects.filter(id__in=[pending.id, running.id, done.id])
        admin_instance.cancel_report_generation_jobs(request, queryset)

        pending.refresh_from_db()
        running.refresh_from_db()
        done.refresh_from_db()

        self.assertEqual(pending.status, ReportGenerationJob.Status.CANCELLED)
        self.assertEqual(running.status, ReportGenerationJob.Status.CANCELLED)
        self.assertEqual(done.status, ReportGenerationJob.Status.DONE)

    def test_cancel_action_includes_children_of_selected_parent(self):
        model = self.generate_models(academy=True)
        parent = self._create_job(None, ReportGenerationJob.Status.DONE, fingerprint="fp-parent")
        child = self._create_job(model.academy, ReportGenerationJob.Status.RUNNING, parent=parent, fingerprint="fp-child")

        request = HttpRequest()
        admin_instance = ReportGenerationJobAdmin(ReportGenerationJob, MagicMock())
        admin_instance.message_user = MagicMock()

        queryset = ReportGenerationJob.objects.filter(id=parent.id)
        admin_instance.cancel_report_generation_jobs(request, queryset)

        child.refresh_from_db()
        self.assertEqual(child.status, ReportGenerationJob.Status.CANCELLED)
