# Generated manually

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("monitoring", "0001_initial"),
        ("admissions", "0002_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="MonitoringError",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "severity",
                    models.CharField(
                        choices=[("MINOR", "Minor"), ("CRITICAL", "Critical")], default="MINOR", max_length=20
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField()),
                ("details", models.JSONField(blank=True, default=dict, help_text="Additional error details as JSON")),
                ("comments", models.JSONField(blank=True, default=dict, help_text="Comments and notes as JSON")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "fixed_at",
                    models.DateTimeField(
                        blank=True, default=None, help_text="When the error was fixed", null=True
                    ),
                ),
                (
                    "replicated_at",
                    models.DateTimeField(
                        blank=True, default=None, help_text="When the error was replicated/verified", null=True
                    ),
                ),
                (
                    "monitor_script",
                    models.ForeignKey(
                        help_text="The script that created this error",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="monitoring_errors",
                        to="monitoring.monitorscript",
                    ),
                ),
                (
                    "academy",
                    models.ForeignKey(
                        help_text="Academy this error belongs to",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="monitoring_errors",
                        to="admissions.academy",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="monitoringerror",
            index=models.Index(fields=["-created_at"], name="monitoring_m_created_idx"),
        ),
        migrations.AddIndex(
            model_name="monitoringerror",
            index=models.Index(fields=["academy", "-created_at"], name="monitoring_m_academy__idx"),
        ),
        migrations.AddIndex(
            model_name="monitoringerror",
            index=models.Index(fields=["monitor_script", "-created_at"], name="monitoring_m_monitor_idx"),
        ),
        migrations.AddIndex(
            model_name="monitoringerror",
            index=models.Index(fields=["severity", "-created_at"], name="monitoring_m_severit_idx"),
        ),
    ]
