# Generated by Django 3.2.9 on 2022-02-11 00:32

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("admissions", "0029_auto_20211217_0248"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("marketing", "0051_auto_20220205_1736"),
    ]

    operations = [
        migrations.CreateModel(
            name="UTMField",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=150, unique=True)),
                ("name", models.CharField(max_length=100)),
                ("description", models.TextField(max_length=450)),
                (
                    "utm_type",
                    models.CharField(
                        choices=[
                            ("CONTENT", "Source"),
                            ("SOURCE", "Medium"),
                            ("MEDIUM", "Content"),
                            ("CAMPAIGN", "Campaign"),
                        ],
                        default=None,
                        max_length=15,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("academy", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="admissions.academy")),
                ("author", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
