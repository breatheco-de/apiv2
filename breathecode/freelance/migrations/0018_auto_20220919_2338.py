# Generated by Django 3.2.15 on 2022-09-19 23:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("freelance", "0017_auto_20220919_2336"),
    ]

    operations = [
        migrations.RenameField(
            model_name="freelanceprojectmember",
            old_name="total_client_price",
            new_name="total_client_hourly_price",
        ),
        migrations.RenameField(
            model_name="freelanceprojectmember",
            old_name="total_cost_price",
            new_name="total_cost_hourly_price",
        ),
    ]
