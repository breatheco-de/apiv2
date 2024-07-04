# Generated by Django 3.2.16 on 2022-11-30 05:04

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("admissions", "0047_merge_20220924_0611"),
        ("notify", "0010_auto_20220901_0323"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("mentorship", "0016_alter_mentorshipbill_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mentorprofile",
            name="status",
            field=models.CharField(
                choices=[
                    ("INVITED", "Invited"),
                    ("ACTIVE", "Active"),
                    ("UNLISTED", "Unlisted"),
                    ("INNACTIVE", "Innactive"),
                ],
                default="INVITED",
                help_text="Options are: INVITED, ACTIVE, UNLISTED, INNACTIVE",
                max_length=15,
            ),
        ),
        migrations.CreateModel(
            name="SupportChannel",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=150)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("academy", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="admissions.academy")),
                (
                    "slack_channel",
                    models.ForeignKey(
                        blank=True, on_delete=django.db.models.deletion.CASCADE, to="notify.slackchannel"
                    ),
                ),
                ("syllabis", models.ManyToManyField(related_name="support_channels", to="admissions.Syllabus")),
            ],
        ),
        migrations.CreateModel(
            name="SupportAgent",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "token",
                    models.CharField(
                        help_text="Used for inviting the user to become a support agent", max_length=255, unique=True
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("INVITED", "Invited"),
                            ("ACTIVE", "Active"),
                            ("UNLISTED", "Unlisted"),
                            ("INNACTIVE", "Innactive"),
                        ],
                        default="INVITED",
                        help_text="Options are: INVITED, ACTIVE, UNLISTED, INNACTIVE",
                        max_length=15,
                    ),
                ),
                (
                    "email",
                    models.CharField(
                        blank=True,
                        default=None,
                        help_text="Only use this if the user does not exist on 4geeks already",
                        max_length=150,
                        null=True,
                    ),
                ),
                ("one_line_bio", models.TextField(blank=True, default=None, max_length=60, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "channel",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="agents",
                        to="mentorship.supportchannel",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        help_text="If the user does not exist, you can use the email field instead",
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
