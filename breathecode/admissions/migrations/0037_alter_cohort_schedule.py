# Generated by Django 3.2.12 on 2022-03-08 11:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("admissions", "0036_rename_specialty_mode_cohort_schedule"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cohort",
            name="schedule",
            field=models.ForeignKey(
                default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to="admissions.syllabusschedule"
            ),
        ),
    ]
