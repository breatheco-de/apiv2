import logging
from typing import Any, Type

from django.core.cache import cache
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone

from breathecode.admissions.models import CohortTimeSlot
from breathecode.admissions.signals import timeslot_saved
from breathecode.events import tasks
from breathecode.events.models import FINISHED, Event
from breathecode.events.signals import event_saved, event_status_updated
from breathecode.monitoring.signals import caxton_webhook
from breathecode.utils.validators.language import language_codes_for_lookup

logger = logging.getLogger(__name__)


@receiver(timeslot_saved, sender=CohortTimeSlot)
def post_save_cohort_time_slot(
    sender: Type[CohortTimeSlot], instance: CohortTimeSlot, force_generation=False, **kwargs: Any
):
    logger.info("Procesing CohortTimeSlot save")

    if force_generation or (
        instance.cohort.ending_date
        and instance.cohort.ending_date > timezone.now()
        and instance.cohort.never_ends == False
    ):
        tasks.build_live_classes_from_timeslot.delay(instance.id)


@receiver(event_status_updated)
def generate_event_recap_on_finished(sender: Type[Event], instance: Event, **kwargs: Any):
    """
    Listen for event status updates and generate a recap when an event is marked as FINISHED.
    """
    logger.info(f"Processing event status update for event {instance.id}")

    # Check if the event status is FINISHED
    if instance.status == FINISHED:
        logger.info(f"Event {instance.id} marked as FINISHED, queuing recap generation")
        tasks.generate_event_recap.delay(instance.id)


@receiver(event_saved)
def invalidate_cache_on_event_saved(sender, instance, **kwargs):
    cache.delete("live_workshop_status")


@receiver(post_delete, sender=Event)
def invalidate_cache_on_event_deleted(sender, instance, **kwargs):
    cache.delete("live_workshop_status")


@receiver(caxton_webhook)
def sync_events_from_caxton_webhook(sender, payload=None, **kwargs: Any):
    """Update workshop events from a Caxton webhook when tracking values changed."""
    if not isinstance(payload, dict):
        return

    items = payload.get("events")
    if not isinstance(items, list):
        return

    for item in items:
        if not isinstance(item, dict) or item.get("type") not in {"entry_common_saved", "entry_locale_saved"}:
            continue

        resource = item.get("resource")
        if not isinstance(resource, dict) or resource.get("contentType") != "workshop":
            continue

        slug = resource.get("slug")
        if not slug:
            continue

        tracking = item.get("tracking") if isinstance(item.get("tracking"), dict) else {}
        updates = {
            field: source[field]
            for source in (item, tracking)
            for field in ("product", "persona", "product_persona", "experiment_id", "variant")
            if field in source
        }

        if not updates:
            continue

        events = Event.objects.filter(slug=slug)
        locale = resource.get("locale")
        if locale:
            codes = language_codes_for_lookup(locale)
            events = events.filter(lang__in=codes or [locale])

        for event in events:
            changed = {field: value for field, value in updates.items() if getattr(event, field) != value}
            if not changed:
                continue
            for field, value in changed.items():
                setattr(event, field, value)
            event.save(update_fields=[*changed, "updated_at"])
