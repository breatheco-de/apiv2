"""AcquisitionReportGenerator: EventCheckin RSVP vs attended rows."""

from datetime import date, datetime

from django.utils import timezone

from breathecode.events.models import Event, EventCheckin
from breathecode.monitoring.reports.acquisition.actions import AcquisitionReportGenerator
from breathecode.monitoring.reports.acquisition.models import AcquisitionReport
from breathecode.monitoring.tests.mixins.monitoring_test_case import MonitoringTestCase


class AcquisitionEventCheckinTests(MonitoringTestCase):
    def _aware(self, y: int, m: int, d: int, hh: int = 12, mm: int = 0) -> datetime:
        return timezone.make_aware(datetime(y, m, d, hh, mm, 0))

    def test_rsvp_only_creates_event_rsvp(self):
        model = self.generate_models(academy=True, event=True, event_kwargs={"slug": "workshop-rsvp"})
        d = date(2026, 4, 10)
        checkin = EventCheckin.objects.create(email="guest@example.com", event=model.event, status="PENDING")
        EventCheckin.objects.filter(pk=checkin.pk).update(created_at=self._aware(2026, 4, 10, 9, 0))

        gen = AcquisitionReportGenerator(report_date=d, academy_id=model.academy.id)
        gen.generate()

        rsvp = AcquisitionReport.objects.filter(
            source_type=AcquisitionReport.SourceType.EVENT_RSVP, source_id=checkin.id
        ).first()
        self.assertIsNotNone(rsvp)
        self.assertEqual(rsvp.funnel_tier, AcquisitionReport.FunnelTier.NURTURE_INVITE)
        self.assertEqual(rsvp.report_date, d)
        self.assertEqual(rsvp.event_slug, "workshop-rsvp")
        self.assertFalse(
            AcquisitionReport.objects.filter(
                source_type=AcquisitionReport.SourceType.EVENT_ATTENDED, source_id=checkin.id
            ).exists()
        )

    def test_attended_only_creates_event_attended(self):
        model = self.generate_models(academy=True, event=True, event_kwargs={"slug": "workshop-done"})
        d = date(2026, 4, 11)
        checkin = EventCheckin.objects.create(email="goer@example.com", event=model.event, status="DONE")
        EventCheckin.objects.filter(pk=checkin.pk).update(
            created_at=self._aware(2026, 3, 1, 8, 0),
            attended_at=self._aware(2026, 4, 11, 18, 0),
        )

        gen = AcquisitionReportGenerator(report_date=d, academy_id=model.academy.id)
        gen.generate()

        att = AcquisitionReport.objects.filter(
            source_type=AcquisitionReport.SourceType.EVENT_ATTENDED, source_id=checkin.id
        ).first()
        self.assertIsNotNone(att)
        self.assertEqual(att.funnel_tier, AcquisitionReport.FunnelTier.SOFT_LEAD)
        self.assertEqual(att.report_date, d)
        self.assertFalse(
            AcquisitionReport.objects.filter(
                source_type=AcquisitionReport.SourceType.EVENT_RSVP, source_id=checkin.id
            ).exists()
        )

    def test_same_day_rsvp_and_attend_creates_two_rows(self):
        model = self.generate_models(academy=True, event=True, event_kwargs={"slug": "same-day"})
        d = date(2026, 4, 12)
        checkin = EventCheckin.objects.create(
            email="both@example.com",
            event=model.event,
            status="DONE",
            utm_source="newsletter",
            utm_campaign="spring",
        )
        ts = self._aware(2026, 4, 12, 10, 0)
        EventCheckin.objects.filter(pk=checkin.pk).update(created_at=ts, attended_at=self._aware(2026, 4, 12, 19, 0))

        gen = AcquisitionReportGenerator(report_date=d, academy_id=model.academy.id)
        gen.generate()

        self.assertEqual(
            AcquisitionReport.objects.filter(
                source_id=checkin.id,
                source_type__in=[
                    AcquisitionReport.SourceType.EVENT_RSVP,
                    AcquisitionReport.SourceType.EVENT_ATTENDED,
                ],
            ).count(),
            2,
        )

    def test_cross_day_rsvp_then_attend_separate_report_dates(self):
        model = self.generate_models(academy=True, event=True, event_kwargs={"slug": "cross"})
        checkin = EventCheckin.objects.create(email="cross@example.com", event=model.event, status="DONE")
        EventCheckin.objects.filter(pk=checkin.pk).update(
            created_at=self._aware(2026, 4, 5, 11, 0),
            attended_at=self._aware(2026, 4, 20, 15, 0),
        )

        AcquisitionReportGenerator(report_date=date(2026, 4, 5), academy_id=model.academy.id).generate()
        AcquisitionReportGenerator(report_date=date(2026, 4, 20), academy_id=model.academy.id).generate()

        rsvp = AcquisitionReport.objects.get(
            source_type=AcquisitionReport.SourceType.EVENT_RSVP, source_id=checkin.id, report_date=date(2026, 4, 5)
        )
        att = AcquisitionReport.objects.get(
            source_type=AcquisitionReport.SourceType.EVENT_ATTENDED, source_id=checkin.id, report_date=date(2026, 4, 20)
        )
        self.assertEqual(rsvp.funnel_tier, AcquisitionReport.FunnelTier.NURTURE_INVITE)
        self.assertEqual(att.funnel_tier, AcquisitionReport.FunnelTier.SOFT_LEAD)

    def test_skips_when_event_has_no_academy(self):
        model = self.generate_models(academy=True, event=True, event_kwargs={"slug": "no-academy"})
        d = date(2026, 4, 15)
        Event.objects.filter(pk=model.event.id).update(academy_id=None)
        checkin = EventCheckin.objects.create(email="orphan@example.com", event=model.event, status="PENDING")
        EventCheckin.objects.filter(pk=checkin.pk).update(created_at=self._aware(2026, 4, 15, 9, 0))

        gen = AcquisitionReportGenerator(report_date=d, academy_id=model.academy.id)
        gen.generate()

        self.assertFalse(AcquisitionReport.objects.filter(source_id=checkin.id).exists())
