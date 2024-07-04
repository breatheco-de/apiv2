# Generated by Django 3.1.4 on 2020-12-29 18:11

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("events", "0017_auto_20201012_2305"),
    ]

    operations = [
        migrations.CreateModel(
            name="EventTicket",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=150)),
                (
                    "status",
                    models.CharField(
                        choices=[("PURCHASED", "Purchased"), ("ATTENDED", "Attended")],
                        default="PURCHASED",
                        max_length=9,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "attendee",
                    models.ForeignKey(
                        blank=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
                    ),
                ),
                ("event", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="events.event")),
            ],
        ),
    ]
