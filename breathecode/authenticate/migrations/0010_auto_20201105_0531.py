# Generated by Django 3.1.2 on 2020-11-05 05:31

import django.contrib.auth.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("admissions", "0011_auto_20201006_0058"),
        ("auth", "0012_alter_user_first_name_max_length"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("authenticate", "0009_auto_20201006_0022"),
    ]

    operations = [
        migrations.CreateModel(
            name="CredentialsSlack",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token", models.CharField(max_length=255)),
                ("bot_user_id", models.CharField(max_length=50)),
                ("app_id", models.CharField(max_length=50)),
                ("authed_user", models.CharField(max_length=50)),
                ("team_id", models.CharField(max_length=50)),
                ("team_name", models.CharField(max_length=100)),
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
        migrations.CreateModel(
            name="ProfileAcademy",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("academy", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="admissions.academy")),
            ],
        ),
        migrations.CreateModel(
            name="Role",
            fields=[
                ("slug", models.SlugField(max_length=25, primary_key=True, serialize=False)),
                ("name", models.CharField(blank=True, default=None, max_length=255, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.DeleteModel(
            name="UserAutentication",
        ),
        migrations.CreateModel(
            name="UserProxy",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("auth.user",),
            managers=[
                ("objects", django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.AddField(
            model_name="profileacademy",
            name="role",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="authenticate.role"),
        ),
        migrations.AddField(
            model_name="profileacademy",
            name="user",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
