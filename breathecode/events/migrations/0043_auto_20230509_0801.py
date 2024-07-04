# Generated by Django 3.2.19 on 2023-05-09 08:01

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("events", "0042_alter_eventtype_icon_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="host_user",
            field=models.ForeignKey(
                blank=True,
                help_text="4geeks user that is the host of the event",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="event_host",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="event",
            name="host",
            field=models.CharField(
                blank=True, default=None, help_text="Host name that appear in Eventbrite", max_length=100, null=True
            ),
        ),
    ]
