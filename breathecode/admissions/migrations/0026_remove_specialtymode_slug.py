# Generated by Django 3.2.9 on 2021-11-08 04:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("admissions", "0025_merge_20211018_2259"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="specialtymode",
            name="slug",
        ),
    ]
