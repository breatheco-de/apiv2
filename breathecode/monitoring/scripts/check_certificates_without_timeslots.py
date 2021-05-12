#!/usr/bin/env python
"""
Checks for certificates without timeslots and sync cohort timeslots and
certificate timeslots
"""
from breathecode.utils import ScriptNotification
from breathecode.admissions.models import Academy, AcademyCertificate, Cohort, CohortTimeSlot, CertificateTimeSlot


# 🔽🔽🔽 Methods
class TimeslotsHandlers:
    def create_cohort_timeslot(self, certificate_timeslot, cohort_id):
        from breathecode.admissions.models import CohortTimeSlot, Cohort
        # for cohort in Cohort.objects.filter(syllabus__certificate__id=certificate_timeslot.certificate.id):

        # cohort_timeslot = CohortTimeSlot.objects.create(
        cohort_timeslot = CohortTimeSlot(
            parent=certificate_timeslot,
            cohort_id=cohort_id,
            starting_at=certificate_timeslot.starting_at,
            ending_at=certificate_timeslot.ending_at,
            recurrent=certificate_timeslot.recurrent,
            recurrency_type=certificate_timeslot.recurrency_type)

        cohort_timeslot.save(force_insert=True)

    def update_cohort_timeslot(self, certificate_timeslot, cohort_timeslot):
        is_change = (
            cohort_timeslot.starting_at != certificate_timeslot.starting_at or
            cohort_timeslot.ending_at != certificate_timeslot.ending_at or
            cohort_timeslot.recurrent != certificate_timeslot.recurrent or
            cohort_timeslot.recurrency_type != certificate_timeslot.recurrency_type
        )

        if not is_change:
            return

        cohort_timeslot.starting_at = certificate_timeslot.starting_at
        cohort_timeslot.ending_at = certificate_timeslot.ending_at
        cohort_timeslot.recurrent = certificate_timeslot.recurrent
        cohort_timeslot.recurrency_type = certificate_timeslot.recurrency_type

        cohort_timeslot.save()


    def create_or_update_cohort_timeslot(self, certificate_timeslot):
        from breathecode.admissions.models import CohortTimeSlot, Cohort
        cohorts = Cohort.objects.filter(syllabus__certificate__id=certificate_timeslot.certificate.id)

        for cohort in cohorts:
            cohort_timeslot = CohortTimeSlot.objects.filter(
                parent__id=certificate_timeslot.id,
                cohort=cohort).first()

            if cohort_timeslot:
                self.update_cohort_timeslot(certificate_timeslot, cohort_timeslot)

            else:
                self.create_cohort_timeslot(certificate_timeslot, cohort.id)


    def append_certificate_slugs(self, certificate_timeslots, slugs_length, index, current_value, slug):
        if not certificate_timeslots and not current_value:
            return slug

        elif not certificate_timeslots and slugs_length > 1 and slugs_length - 1 == index:
            return f'{current_value} and {slug}'

        elif not certificate_timeslots:
            return f'{current_value}, {slug}'


# 🔽🔽🔽 Implementation
certificates_slugs = (AcademyCertificate.objects.filter(academy__id=academy.id)
    .values_list('certificate__slug', flat=True))
slugs_length = len(certificates_slugs)
certificates_slugs_without_timeslots = ''

handler = TimeslotsHandlers()

for index in range(0, slugs_length):
    slug = certificates_slugs[index]
    certificate_timeslots = CertificateTimeSlot.objects.filter(certificate__slug=slug)

    certificates_slugs_without_timeslots = handler.append_certificate_slugs(
        certificate_timeslots,
        slugs_length,
        index,
        certificates_slugs_without_timeslots,
        slug)

    for certificate_timeslot in certificate_timeslots:
        handler.create_or_update_cohort_timeslot(certificate_timeslot)

if certificates_slugs_without_timeslots:
    raise ScriptNotification(
        f"This certificates: {certificates_slugs_without_timeslots} don't have timeslots",
        slug='certificates-without-timeslots')

print('Done!')
