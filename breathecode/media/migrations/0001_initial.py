# Generated by Django 5.2 on 2025-05-16 04:21

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("admissions", "0002_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=150, unique=True)),
                ("name", models.CharField(max_length=150)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="MediaResolution",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("hash", models.CharField(max_length=64)),
                ("width", models.IntegerField()),
                ("height", models.IntegerField()),
                ("hits", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="Chunk",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("mime", models.CharField(max_length=60)),
                ("chunk_index", models.PositiveIntegerField()),
                ("total_chunks", models.PositiveIntegerField()),
                ("chunk_size", models.PositiveIntegerField(help_text="Size of each chunk in bytes")),
                ("bucket", models.CharField(max_length=255)),
                ("operation_type", models.CharField(max_length=60)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "academy",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        help_text="Academy where the file was uploaded",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="admissions.academy",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        help_text="User who uploaded the file",
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="File",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("mime", models.CharField(max_length=60)),
                ("hash", models.CharField(max_length=64)),
                ("size", models.PositiveIntegerField(blank=True, null=True)),
                ("bucket", models.CharField(max_length=255)),
                ("operation_type", models.CharField(max_length=60)),
                (
                    "meta",
                    models.JSONField(
                        blank=True,
                        default=None,
                        help_text="Metadata associated with the file, used for schedule the transfer",
                        null=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("CREATED", "Created"),
                            ("TRANSFERRING", "Transferring"),
                            ("TRANSFERRED", "Transferred"),
                            ("ERROR", "Error"),
                        ],
                        default="CREATED",
                        max_length=12,
                    ),
                ),
                ("status_message", models.CharField(blank=True, default=None, max_length=255, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "academy",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        help_text="Academy where the file was uploaded",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="admissions.academy",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        help_text="User who uploaded the file",
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Media",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=150, unique=True)),
                ("name", models.CharField(max_length=150)),
                ("mime", models.CharField(max_length=60)),
                ("url", models.URLField(max_length=255)),
                ("thumbnail", models.URLField(blank=True, max_length=255, null=True)),
                ("hash", models.CharField(max_length=64)),
                ("hits", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "academy",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="admissions.academy"
                    ),
                ),
                ("categories", models.ManyToManyField(blank=True, to="media.category")),
            ],
        ),
    ]
