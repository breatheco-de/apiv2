# Generated by Django 5.1.7 on 2025-04-07 19:51

import breathecode.payments.models
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("admissions", "0068_merge_20241216_1552"),
        ("payments", "0058_alter_planfinancing_status_alter_subscription_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="academyservice",
            name="pricing_ratio_exceptions",
            field=models.JSONField(
                blank=True, default=dict, help_text="Exceptions to the general pricing ratios per country"
            ),
        ),
        migrations.AddField(
            model_name="bag",
            name="country_code",
            field=models.CharField(
                blank=True,
                default=None,
                help_text="Country code used for pricing ratio calculations",
                max_length=2,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="bag",
            name="pricing_ratio_explanation",
            field=models.JSONField(
                blank=True,
                default=breathecode.payments.models._default_pricing_ratio_explanation,
                help_text="Explanation of which exceptions were applied to calculate price",
            ),
        ),
        migrations.AddField(
            model_name="plan",
            name="pricing_ratio_exceptions",
            field=models.JSONField(
                blank=True, default=dict, help_text="Exceptions to the general pricing ratios per country"
            ),
        ),
        migrations.CreateModel(
            name="AcademyPaymentSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "pos_vendor",
                    models.CharField(
                        choices=[("STRIPE", "Stripe")],
                        default="STRIPE",
                        help_text="Point of Sale vendor like Stripe, etc.",
                        max_length=20,
                    ),
                ),
                ("pos_api_key", models.CharField(blank=True, help_text="API key for the POS vendor", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "academy",
                    models.OneToOneField(
                        help_text="Academy",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payment_settings",
                        to="admissions.academy",
                    ),
                ),
            ],
        ),
    ]
