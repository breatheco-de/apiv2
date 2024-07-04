# Generated by Django 3.0.7 on 2020-06-16 06:25

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CredentialsGithub",
            fields=[
                ("github_id", models.IntegerField(primary_key=True, serialize=False)),
                ("token", models.CharField(max_length=255)),
                ("email", models.CharField(max_length=150, unique=True)),
                ("avatar_url", models.CharField(max_length=255)),
                ("name", models.CharField(max_length=150)),
                ("blog", models.CharField(max_length=150)),
                ("bio", models.CharField(max_length=255)),
                ("company", models.CharField(max_length=150)),
                ("twitter_username", models.CharField(blank=True, max_length=50, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        blank=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
        ),
    ]
