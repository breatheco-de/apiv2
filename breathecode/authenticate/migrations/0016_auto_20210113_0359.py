# Generated by Django 3.1.4 on 2021-01-13 03:59

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("admissions", "0014_auto_20201218_0534"),
        ("authenticate", "0015_profile_show_tutorial"),
    ]

    operations = [
        migrations.AddField(
            model_name="profileacademy",
            name="email",
            field=models.CharField(default=None, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name="profileacademy",
            name="status",
            field=models.CharField(
                choices=[("INVITED", "Invited"), ("ACTIVE", "Active")], default="INVITED", max_length=15
            ),
        ),
        migrations.AlterField(
            model_name="profileacademy",
            name="user",
            field=models.ForeignKey(
                default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.CreateModel(
            name="UserInvite",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.CharField(default=None, max_length=150, null=True)),
                ("first_name", models.CharField(default=None, max_length=100, null=True)),
                ("last_name", models.CharField(default=None, max_length=100, null=True)),
                ("token", models.CharField(max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[("PENDING", "Pending"), ("ACCEPTED", "Accepted")], default="PENDING", max_length=15
                    ),
                ),
                (
                    "phone",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=17,
                        validators=[
                            django.core.validators.RegexValidator(
                                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
                                regex="^\\+?1?\\d{9,15}$",
                            )
                        ],
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "academy",
                    models.ForeignKey(
                        default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to="admissions.academy"
                    ),
                ),
                ("author", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                (
                    "cohort",
                    models.ForeignKey(
                        default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to="admissions.cohort"
                    ),
                ),
                (
                    "role",
                    models.ForeignKey(
                        default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to="authenticate.role"
                    ),
                ),
            ],
        ),
    ]
