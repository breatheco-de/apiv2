# Generated by Django 3.1.3 on 2020-11-10 23:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("admissions", "0011_auto_20201006_0058"),
        ("feedback", "0010_auto_20201029_0857"),
    ]

    operations = [
        migrations.CreateModel(
            name="CohortUserProxy",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("admissions.cohortuser",),
        ),
    ]
