# Generated by Django 3.2.12 on 2022-03-25 21:03

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("assessment", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Asset",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=200, unique=True)),
                ("title", models.CharField(blank=True, max_length=200)),
                (
                    "lang",
                    models.CharField(blank=True, default=None, help_text="E.g: en, es, it", max_length=2, null=True),
                ),
                ("url", models.URLField()),
                ("solution_url", models.URLField(blank=True, default=None, null=True)),
                ("preview", models.URLField(blank=True, default=None, null=True)),
                ("description", models.TextField(blank=True, default=None, null=True)),
                (
                    "readme_url",
                    models.URLField(
                        blank=True, default=None, help_text="This will be used to synch from github", null=True
                    ),
                ),
                ("intro_video_url", models.URLField(blank=True, default=None, null=True)),
                ("solution_video_url", models.URLField(blank=True, default=None, null=True)),
                ("readme", models.TextField(blank=True, default=None, null=True)),
                ("config", models.JSONField(blank=True, default=None, null=True)),
                (
                    "external",
                    models.BooleanField(
                        default=False,
                        help_text="External assets will open in a new window, they are not built using breathecode or learnpack tecnology",
                    ),
                ),
                ("interactive", models.BooleanField(default=False)),
                ("with_solutions", models.BooleanField(default=False)),
                ("with_video", models.BooleanField(default=False)),
                ("graded", models.BooleanField(default=False)),
                ("gitpod", models.BooleanField(default=False)),
                ("duration", models.IntegerField(blank=True, default=None, help_text="In hours", null=True)),
                (
                    "difficulty",
                    models.CharField(
                        blank=True,
                        choices=[("BEGINNER", "Beginner"), ("EASY", "Easy")],
                        default=None,
                        max_length=20,
                        null=True,
                    ),
                ),
                (
                    "visibility",
                    models.CharField(
                        choices=[("PUBLIC", "Public"), ("UNLISTED", "Unlisted"), ("PRIVATE", "Private")],
                        default="PUBLIC",
                        max_length=20,
                    ),
                ),
                (
                    "asset_type",
                    models.CharField(
                        choices=[
                            ("PROJECT", "Project"),
                            ("EXERCISE", "Exercise"),
                            ("QUIZ", "Quiz"),
                            ("LESSON", "Lesson"),
                            ("VIDEO", "Video"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("UNNASIGNED", "Unnasigned"), ("DRAFT", "Draft"), ("OK", "Ok")],
                        default="DRAFT",
                        help_text="Related to the publishing of the asset",
                        max_length=20,
                    ),
                ),
                (
                    "sync_status",
                    models.CharField(
                        blank=True,
                        choices=[("PENDING", "Pending"), ("ERROR", "Error"), ("OK", "Ok"), ("WARNING", "Warning")],
                        default=None,
                        help_text="Internal state automatically set by the system based on sync",
                        max_length=20,
                        null=True,
                    ),
                ),
                (
                    "test_status",
                    models.CharField(
                        blank=True,
                        choices=[("PENDING", "Pending"), ("ERROR", "Error"), ("OK", "Ok"), ("WARNING", "Warning")],
                        default=None,
                        help_text="Internal state automatically set by the system based on test",
                        max_length=20,
                        null=True,
                    ),
                ),
                ("last_synch_at", models.DateTimeField(blank=True, default=None, null=True)),
                ("last_test_at", models.DateTimeField(blank=True, default=None, null=True)),
                (
                    "status_text",
                    models.TextField(
                        blank=True, default=None, help_text="Used by the sych status to provide feedback", null=True
                    ),
                ),
                (
                    "authors_username",
                    models.CharField(
                        blank=True,
                        default=None,
                        help_text="Github usernames separated by comma",
                        max_length=80,
                        null=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "all_translations",
                    models.ManyToManyField(
                        blank=True, related_name="_registry_asset_all_translations_+", to="registry.Asset"
                    ),
                ),
                (
                    "assessment",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        help_text="Connection with the assessment breathecode app",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="assessment.assessment",
                    ),
                ),
                (
                    "author",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        help_text="Who wrote the lesson, not necessarily the owner",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        help_text="The owner has the github premissions to update the lesson",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="owned_lessons",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="AssetTechnology",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=200, unique=True)),
                ("title", models.CharField(blank=True, max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name="AssetErrorLog",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "asset_type",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("PROJECT", "Project"),
                            ("EXERCISE", "Exercise"),
                            ("QUIZ", "Quiz"),
                            ("LESSON", "Lesson"),
                            ("VIDEO", "Video"),
                        ],
                        default=None,
                        max_length=20,
                        null=True,
                    ),
                ),
                ("slug", models.SlugField(max_length=200)),
                (
                    "status",
                    models.CharField(
                        choices=[("ERROR", "Error"), ("FIXED", "Fixed"), ("IGNORED", "Ignored")],
                        default="ERROR",
                        max_length=20,
                    ),
                ),
                ("path", models.CharField(max_length=200)),
                (
                    "status_text",
                    models.TextField(
                        blank=True,
                        default=None,
                        help_text="Status details, it may be set automatically if enough error information",
                        null=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "asset",
                    models.ForeignKey(
                        default=None,
                        help_text='Assign an asset to this error and you will be able to create an alias for it from the django admin bulk actions "create alias"',
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="registry.asset",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        default=None,
                        help_text="The user how asked for the asset and got the error",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="AssetAlias",
            fields=[
                ("slug", models.SlugField(max_length=200, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("asset", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="registry.asset")),
            ],
        ),
        migrations.AddField(
            model_name="asset",
            name="technologies",
            field=models.ManyToManyField(to="registry.AssetTechnology"),
        ),
    ]
