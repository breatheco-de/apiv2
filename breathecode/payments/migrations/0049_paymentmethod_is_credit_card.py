# Generated by Django 5.0.6 on 2024-06-26 21:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0048_remove_serviceset_academy_remove_serviceset_services_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymentmethod",
            name="is_credit_card",
            field=models.BooleanField(default=False),
        ),
    ]
