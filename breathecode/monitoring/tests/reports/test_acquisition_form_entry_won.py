"""AcquisitionReportGenerator: FORM_ENTRY vs FORM_ENTRY_WON by created_at vs won_at."""

from datetime import date, datetime

from django.utils import timezone

from breathecode.marketing.models import PENDING, WON, FormEntry
from breathecode.monitoring.reports.acquisition.actions import AcquisitionReportGenerator
from breathecode.monitoring.reports.acquisition.models import AcquisitionReport
from breathecode.monitoring.tests.mixins.monitoring_test_case import MonitoringTestCase


class AcquisitionFormEntryWonTests(MonitoringTestCase):
    def _aware(self, y: int, m: int, d: int, hh: int = 12, mm: int = 0) -> datetime:
        return timezone.make_aware(datetime(y, m, d, hh, mm, 0))

    def test_win_day_only_creates_form_entry_won_not_form_entry(self):
        model = self.generate_models(academy=True)
        entry = FormEntry.objects.create(
            academy=model.academy,
            email="wononly@example.com",
            first_name="W",
            last_name="O",
            storage_status=PENDING,
            deal_status=WON,
        )
        FormEntry.objects.filter(pk=entry.pk).update(
            created_at=self._aware(2026, 3, 1, 9, 0),
            won_at=self._aware(2026, 4, 15, 14, 0),
        )

        win_day = date(2026, 4, 15)
        AcquisitionReportGenerator(report_date=win_day, academy_id=model.academy.id).generate()

        won = AcquisitionReport.objects.filter(
            source_type=AcquisitionReport.SourceType.FORM_ENTRY_WON, source_id=entry.id
        ).first()
        self.assertIsNotNone(won)
        self.assertEqual(won.report_date, win_day)
        self.assertEqual(won.funnel_tier, AcquisitionReport.FunnelTier.WON_OR_SALE)
        self.assertFalse(
            AcquisitionReport.objects.filter(
                source_type=AcquisitionReport.SourceType.FORM_ENTRY,
                source_id=entry.id,
                report_date=win_day,
            ).exists()
        )

    def test_creation_day_only_form_entry(self):
        model = self.generate_models(academy=True)
        entry = FormEntry.objects.create(
            academy=model.academy,
            email="new@example.com",
            first_name="N",
            last_name="E",
            storage_status=PENDING,
            deal_status=None,
        )
        create_day = date(2026, 5, 1)
        FormEntry.objects.filter(pk=entry.pk).update(
            created_at=self._aware(2026, 5, 1, 10, 0),
            won_at=None,
        )

        AcquisitionReportGenerator(report_date=create_day, academy_id=model.academy.id).generate()

        fe = AcquisitionReport.objects.filter(
            source_type=AcquisitionReport.SourceType.FORM_ENTRY, source_id=entry.id, report_date=create_day
        ).first()
        self.assertIsNotNone(fe)
        self.assertFalse(
            AcquisitionReport.objects.filter(
                source_type=AcquisitionReport.SourceType.FORM_ENTRY_WON, source_id=entry.id
            ).exists()
        )

    def test_same_calendar_day_create_and_win_creates_both_rows(self):
        model = self.generate_models(academy=True)
        entry = FormEntry.objects.create(
            academy=model.academy,
            email="same@example.com",
            first_name="S",
            last_name="D",
            storage_status=PENDING,
            deal_status=WON,
        )
        d = date(2026, 6, 10)
        ts = self._aware(2026, 6, 10, 8, 0)
        FormEntry.objects.filter(pk=entry.pk).update(created_at=ts, won_at=self._aware(2026, 6, 10, 20, 0))

        AcquisitionReportGenerator(report_date=d, academy_id=model.academy.id).generate()

        types = set(
            AcquisitionReport.objects.filter(source_id=entry.id, report_date=d).values_list(
                "source_type", flat=True
            )
        )
        self.assertEqual(
            types,
            {
                AcquisitionReport.SourceType.FORM_ENTRY,
                AcquisitionReport.SourceType.FORM_ENTRY_WON,
            },
        )
