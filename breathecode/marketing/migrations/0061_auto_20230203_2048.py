# Generated by Django 3.2.16 on 2023-02-03 20:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("marketing", "0060_auto_20221109_2245"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="formentry",
            name="automation_objects",
        ),
        migrations.RemoveField(
            model_name="formentry",
            name="tag_objects",
        ),
    ]
