import logging
from datetime import timedelta

from django.dispatch import receiver

from breathecode.admissions.models import Academy
from breathecode.admissions.signals import academy_reseller_changed
from breathecode.monitoring import signals
from breathecode.monitoring.models import Application, MonitorScript

logger = logging.getLogger(__name__)


@receiver(signals.application_created, sender=Application)
def application_created(sender, instance, **kwargs):
    missing_stripe_slug = "alert_missing_stripe_credentials"
    if instance.academy.reseller:
        MonitorScript.objects.create(
            application=instance,
            script_slug=missing_stripe_slug,
            frequency_delta=timedelta(days=7),
        )


@receiver(academy_reseller_changed, sender=Academy)
def on_academy_reseller_changed(sender, instance, value, **kwargs):
    monitor_script = MonitorScript.objects.filter(
        script_slug="alert_missing_stripe_credentials",
        application__academy=instance,
    ).first()

    if value:
        if not monitor_script:
            application = Application.objects.filter(academy=instance).first()
            if application:
                MonitorScript.objects.create(
                    application=application,
                    script_slug="alert_missing_stripe_credentials",
                    frequency_delta=timedelta(days=7),
                )
    else:
        if monitor_script:
            monitor_script.delete()
