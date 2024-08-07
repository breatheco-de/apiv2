# Generated by Django 3.2.16 on 2023-04-10 15:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("authenticate", "0035_alter_academyauthsettings_github_default_team_ids"),
    ]

    operations = [
        migrations.CreateModel(
            name="GithubAcademyUserLog",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "storage_status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("SYNCHED", "Synched"),
                            ("ERROR", "Error"),
                            ("UNKNOWN", "Unknown"),
                        ],
                        default="PENDING",
                        max_length=20,
                    ),
                ),
                (
                    "storage_action",
                    models.CharField(
                        choices=[("ADD", "Add"), ("DELETE", "Delete"), ("INVITE", "Invite"), ("IGNORE", "Ignore")],
                        default="ADD",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "academy_user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="authenticate.githubacademyuser"),
                ),
            ],
        ),
    ]
