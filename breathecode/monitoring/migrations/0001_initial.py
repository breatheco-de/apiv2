# Generated by Django 5.2 on 2025-05-16 04:20

import datetime
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("admissions", "0002_initial"),
        ("notify", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="NoPagination",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("path", models.CharField(max_length=255)),
                ("method", models.CharField(max_length=9)),
            ],
        ),
        migrations.CreateModel(
            name="RepositoryWebhook",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "webhook_action",
                    models.CharField(
                        blank=True,
                        default=None,
                        help_text="The specific action that was triggered on github for this webhook",
                        max_length=100,
                        null=True,
                    ),
                ),
                (
                    "scope",
                    models.CharField(
                        blank=True,
                        default=None,
                        help_text="The specific entity that triggered this webhook, for example: issues, issues_comment, etc.",
                        max_length=100,
                        null=True,
                    ),
                ),
                (
                    "run_at",
                    models.DateTimeField(
                        blank=True, default=None, help_text="Date/time that the webhook ran", null=True
                    ),
                ),
                ("repository", models.URLField(help_text="Github repo where the event occured", max_length=255)),
                (
                    "payload",
                    models.JSONField(
                        help_text="Info that came on the request, it varies depending on the webhook type"
                    ),
                ),
                ("academy_slug", models.SlugField()),
                (
                    "status",
                    models.CharField(
                        choices=[("PENDING", "Pending"), ("DONE", "Done"), ("ERROR", "Error")],
                        default="PENDING",
                        max_length=9,
                    ),
                ),
                ("status_text", models.CharField(blank=True, default=None, max_length=255, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="StripeEvent",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "stripe_id",
                    models.CharField(blank=True, default=None, help_text="Stripe id", max_length=32, null=True),
                ),
                ("type", models.CharField(help_text="Stripe event type", max_length=50)),
                (
                    "status",
                    models.CharField(
                        choices=[("PENDING", "Pending"), ("DONE", "Done"), ("ERROR", "Error")],
                        default="PENDING",
                        max_length=9,
                    ),
                ),
                ("status_texts", models.JSONField(blank=True, default=dict)),
                ("data", models.JSONField(blank=True, default=dict)),
                ("request", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="Supervisor",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("task_module", models.CharField(max_length=200)),
                ("task_name", models.CharField(max_length=200)),
                (
                    "delta",
                    models.DurationField(
                        default=datetime.timedelta(seconds=1800),
                        help_text="How long to wait for the next execution, defaults to 30 minutes",
                    ),
                ),
                ("ran_at", models.DateTimeField(blank=True, default=None, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="Application",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=100)),
                ("status_text", models.CharField(blank=True, default=None, max_length=255, null=True)),
                (
                    "notify_email",
                    models.CharField(
                        blank=True, default=None, help_text="Comma separated list of emails", max_length=255, null=True
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("LOADING", "Loading"),
                            ("OPERATIONAL", "Operational"),
                            ("MINOR", "Minor"),
                            ("CRITICAL", "Critical"),
                        ],
                        default="OPERATIONAL",
                        max_length=20,
                    ),
                ),
                (
                    "paused_until",
                    models.DateTimeField(
                        blank=True,
                        default=None,
                        help_text="if you want to stop checking for a period of time",
                        null=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("academy", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="admissions.academy")),
                (
                    "notify_slack_channel",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        help_text="Please pick an academy first to be able to see the available slack channels to notify",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="notify.slackchannel",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="CSVDownload",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("url", models.URLField()),
                (
                    "status",
                    models.CharField(
                        choices=[("LOADING", "Loading"), ("ERROR", "Error"), ("DONE", "Done")],
                        default="LOADING",
                        max_length=20,
                    ),
                ),
                ("status_message", models.TextField(blank=True, default=None, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("finished_at", models.DateTimeField(auto_now=True)),
                (
                    "academy",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="admissions.academy",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="CSVUpload",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("url", models.URLField()),
                (
                    "status",
                    models.CharField(
                        choices=[("PENDING", "Pending"), ("ERROR", "Error"), ("DONE", "Done")],
                        default="PENDING",
                        max_length=20,
                    ),
                ),
                ("status_message", models.TextField(blank=True, default=None, null=True)),
                ("log", models.CharField(max_length=50)),
                ("hash", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("finished_at", models.DateTimeField(auto_now=True)),
                (
                    "academy",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="admissions.academy",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Endpoint",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("url", models.CharField(max_length=255)),
                (
                    "test_pattern",
                    models.CharField(
                        blank=True,
                        default=None,
                        help_text="If left blank sys will only ping",
                        max_length=100,
                        null=True,
                    ),
                ),
                ("frequency_in_minutes", models.FloatField(default=30)),
                ("status_code", models.IntegerField(default=200)),
                ("severity_level", models.IntegerField(default=0)),
                ("status_text", models.CharField(blank=True, default=None, editable=False, max_length=255, null=True)),
                (
                    "special_status_text",
                    models.CharField(
                        blank=True,
                        default=None,
                        help_text="Add a message for people to see when is down",
                        max_length=255,
                        null=True,
                    ),
                ),
                ("response_text", models.TextField(blank=True, default=None, null=True)),
                ("last_check", models.DateTimeField(blank=True, default=None, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("LOADING", "Loading"),
                            ("OPERATIONAL", "Operational"),
                            ("MINOR", "Minor"),
                            ("CRITICAL", "Critical"),
                        ],
                        default="OPERATIONAL",
                        max_length=20,
                    ),
                ),
                (
                    "paused_until",
                    models.DateTimeField(
                        blank=True,
                        default=None,
                        help_text="if you want to stop checking for a period of time",
                        null=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "application",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="monitoring.application"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="MonitorScript",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("script_slug", models.SlugField(blank=True, default=None, null=True)),
                ("script_body", models.TextField(blank=True, default=None, null=True)),
                (
                    "frequency_delta",
                    models.DurationField(
                        default=datetime.timedelta(seconds=1800),
                        help_text="How long to wait for the next execution, defaults to 30 minutes",
                    ),
                ),
                ("status_code", models.IntegerField(default=200)),
                ("severity_level", models.IntegerField(default=0)),
                (
                    "notify_email",
                    models.CharField(
                        blank=True,
                        default=None,
                        help_text="Only specify if need to override the application.notify_email, you can add many comma separated.",
                        max_length=255,
                        null=True,
                    ),
                ),
                ("status_text", models.CharField(blank=True, default=None, editable=False, max_length=255, null=True)),
                (
                    "special_status_text",
                    models.CharField(
                        blank=True,
                        default=None,
                        help_text="Add a message for people to see when is down",
                        max_length=255,
                        null=True,
                    ),
                ),
                ("response_text", models.TextField(blank=True, default=None, null=True)),
                ("last_run", models.DateTimeField(blank=True, default=None, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("LOADING", "Loading"),
                            ("OPERATIONAL", "Operational"),
                            ("MINOR", "Minor"),
                            ("CRITICAL", "Critical"),
                        ],
                        default="OPERATIONAL",
                        max_length=20,
                    ),
                ),
                (
                    "paused_until",
                    models.DateTimeField(
                        blank=True,
                        default=None,
                        help_text="if you want to stop checking for a period of time",
                        null=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "application",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="monitoring.application"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="RepositorySubscription",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("repository", models.URLField(help_text="Github repo where the event ocurred", max_length=255)),
                ("token", models.CharField(max_length=255, unique=True)),
                ("hook_id", models.IntegerField(blank=True, default=None, help_text="Assigned from github", null=True)),
                (
                    "last_call",
                    models.DateTimeField(
                        blank=True,
                        default=None,
                        help_text="Last time github notified updates on this repo subscription",
                        null=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("OPERATIONAL", "Operational"), ("CRITICAL", "Critical"), ("DISABLED", "Disabled")],
                        default="CRITICAL",
                        max_length=20,
                    ),
                ),
                ("status_message", models.TextField(blank=True, default="Waiting for ping", null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="admissions.academy")),
                (
                    "shared_with",
                    models.ManyToManyField(blank=True, related_name="repo_subscription", to="admissions.academy"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="SupervisorIssue",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("occurrences", models.PositiveIntegerField(blank=True, default=1)),
                ("attempts", models.PositiveIntegerField(blank=True, default=0)),
                ("code", models.SlugField(blank=True, default=None, null=True)),
                ("params", models.JSONField(blank=True, default=None, null=True)),
                ("fixed", models.BooleanField(blank=True, default=None, null=True)),
                ("error", models.TextField(max_length=255)),
                ("ran_at", models.DateTimeField(blank=True, default=None, null=True)),
                (
                    "supervisor",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="monitoring.supervisor"),
                ),
            ],
        ),
    ]
