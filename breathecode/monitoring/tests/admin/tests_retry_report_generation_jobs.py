from datetime import date
from unittest.mock import MagicMock, patch

from django.http.request import HttpRequest

from ..mixins import MonitoringTestCase
from ...admin import ReportGenerationJobAdmin
from ...models import ReportGenerationJob


class ReportGenerationJobRetryActionTests(MonitoringTestCase):
    def _run_retry_action_with_commit_callbacks(self, admin_instance, request, queryset, delay_mock):
        pending = []

        def capture_on_commit(fn):
            pending.append(fn)

        with patch("breathecode.monitoring.admin.transaction.on_commit", side_effect=capture_on_commit):
            with patch("breathecode.monitoring.admin.generate_report_job", delay_mock):
                admin_instance.retry_report_generation_jobs(request, queryset)
                for fn in pending:
                    fn()

    def _create_job(self, academy, status, parent=None, fingerprint="f-1", celery_task_id=None):
        return ReportGenerationJob.objects.create(
            report_type=ReportGenerationJob.ReportType.ACQUISITION,
            status=status,
            academy=academy,
            parent=parent,
            date_start=date(2026, 4, 1),
            date_end=date(2026, 4, 1),
            params={"date": "2026-04-01"},
            fingerprint=fingerprint,
            celery_task_id=celery_task_id,
            progress_current=3,
            progress_total=10,
            generated_rows=99,
        )

    def test_retry_action_resets_pending_and_enqueues(self):
        model = self.generate_models(academy=True)
        pending = self._create_job(
            model.academy,
            ReportGenerationJob.Status.PENDING,
            fingerprint="fp-p",
            celery_task_id="stale-task-id",
        )

        request = HttpRequest()
        admin_instance = ReportGenerationJobAdmin(ReportGenerationJob, MagicMock())
        admin_instance.message_user = MagicMock()

        delay_mock = MagicMock()
        delay_mock.delay.return_value = MagicMock(id="new-celery-id")

        queryset = ReportGenerationJob.objects.filter(id=pending.id)
        self._run_retry_action_with_commit_callbacks(admin_instance, request, queryset, delay_mock)

        pending.refresh_from_db()
        self.assertEqual(pending.status, ReportGenerationJob.Status.PENDING)
        self.assertEqual(pending.status_message, "Queued (admin retry)")
        self.assertEqual(pending.celery_task_id, "new-celery-id")
        self.assertEqual(pending.progress_current, 0)
        self.assertEqual(pending.progress_total, 0)
        self.assertEqual(pending.generated_rows, 0)
        delay_mock.delay.assert_called_once_with(pending.id)

    def test_retry_action_includes_children_of_selected_parent(self):
        model = self.generate_models(academy=True)
        parent = self._create_job(None, ReportGenerationJob.Status.PENDING, fingerprint="fp-parent")
        child = self._create_job(
            model.academy,
            ReportGenerationJob.Status.PENDING,
            parent=parent,
            fingerprint="fp-child",
            celery_task_id="old",
        )

        request = HttpRequest()
        admin_instance = ReportGenerationJobAdmin(ReportGenerationJob, MagicMock())
        admin_instance.message_user = MagicMock()

        delay_mock = MagicMock()
        delay_mock.delay.return_value = MagicMock(id="retry-id")

        queryset = ReportGenerationJob.objects.filter(id=parent.id)
        self._run_retry_action_with_commit_callbacks(admin_instance, request, queryset, delay_mock)

        child.refresh_from_db()
        self.assertEqual(child.celery_task_id, "retry-id")
        delay_mock.delay.assert_called_once_with(child.id)

    def test_retry_action_skips_done_and_running(self):
        model = self.generate_models(academy=True)
        done = self._create_job(model.academy, ReportGenerationJob.Status.DONE, fingerprint="fp-d")
        running = self._create_job(model.academy, ReportGenerationJob.Status.RUNNING, fingerprint="fp-r")

        request = HttpRequest()
        admin_instance = ReportGenerationJobAdmin(ReportGenerationJob, MagicMock())
        admin_instance.message_user = MagicMock()

        delay_mock = MagicMock()

        queryset = ReportGenerationJob.objects.filter(id__in=[done.id, running.id])
        self._run_retry_action_with_commit_callbacks(admin_instance, request, queryset, delay_mock)

        delay_mock.delay.assert_not_called()
