# Generated by Django 3.0.7 on 2020-06-18 18:29

import phonenumber_field.modelfields
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Contact",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("first_name", models.CharField(max_length=150)),
                ("last_name", models.CharField(max_length=150)),
                ("email", models.CharField(max_length=150)),
                ("phone", phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=128, region=None)),
                ("course", models.CharField(max_length=2)),
                ("client_comments", models.CharField(max_length=2)),
                ("language", models.CharField(max_length=2)),
                ("utm_url", models.CharField(max_length=2)),
                ("utm_medium", models.CharField(max_length=2)),
                ("utm_campaign", models.CharField(max_length=2)),
                ("street_address", models.CharField(max_length=250)),
                ("country", models.CharField(max_length=30)),
                ("city", models.CharField(max_length=30)),
                ("latitude", models.DecimalField(decimal_places=6, max_digits=9)),
                ("longitude", models.DecimalField(decimal_places=6, max_digits=9)),
                ("state", models.CharField(max_length=30)),
                ("zip_code", models.IntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
