# Generated by Django 3.2.12 on 2022-03-04 19:26

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("admissions", "0034_rename_specialtymodetimeslot_syllabusscheduletimeslot"),
    ]

    operations = [
        migrations.RenameField(
            model_name="syllabusscheduletimeslot",
            old_name="specialty_mode",
            new_name="schedule",
        ),
    ]
