#!/usr/bin/env python
"""
Checks for certificates without timeslots and sync cohort timeslots and
certificate timeslots
"""
from breathecode.utils import ScriptNotification
from breathecode.admissions.models import AcademyCertificate, CertificateTimeSlot


def append_certificate_slugs(exists, slugs_length, index, current_value, slug):
    if not exists and not current_value:
        return slug

    elif not exists and slugs_length > 1 and slugs_length - 1 == index:
        return f'{current_value} and {slug}'

    elif not exists:
        return f'{current_value}, {slug}'


certificates_slugs = (AcademyCertificate.objects.filter(academy__id=academy.id)
    .values_list('certificate__slug', flat=True))
slugs_length = len(certificates_slugs)
certificates_slugs_without_timeslots = ''

for index in range(0, slugs_length):
    slug = certificates_slugs[index]
    exists = CertificateTimeSlot.objects.filter(certificate__slug=slug).exists()

    certificates_slugs_without_timeslots = append_certificate_slugs(
        exists,
        slugs_length,
        index,
        certificates_slugs_without_timeslots,
        slug)

if certificates_slugs_without_timeslots:
    raise ScriptNotification(
        f"This certificates: {certificates_slugs_without_timeslots} don't have timeslots",
        slug='certificates-without-timeslots')

print('Done!')
