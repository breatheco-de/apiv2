# Data migration: copy specialty.syllabus into specialty.syllabuses (ManyToMany)
# so that all specialties that had the OneToOne syllabus set now have it in syllabuses.

from django.db import migrations


def migrate_syllabus_to_syllabuses(apps, schema_editor):
    Specialty = apps.get_model("certificate", "Specialty")
    for specialty in Specialty.objects.filter(syllabus__isnull=False):
        if not specialty.syllabuses.filter(pk=specialty.syllabus_id).exists():
            specialty.syllabuses.add(specialty.syllabus)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("certificate", "0004_specialty_academy"),
    ]

    operations = [
        migrations.RunPython(migrate_syllabus_to_syllabuses, noop_reverse),
    ]
