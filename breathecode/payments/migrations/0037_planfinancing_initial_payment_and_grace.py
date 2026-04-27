from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0036_planfinancing_next_charge_pull_applied_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="planfinancing",
            name="initial_payment_amount",
            field=models.FloatField(
                blank=True,
                default=None,
                help_text="Amount paid when this plan financing was created by staff.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="planfinancing",
            name="initial_payment_notes",
            field=models.CharField(
                blank=True,
                default=None,
                help_text="Optional staff notes about the initial payment.",
                max_length=250,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="planfinancing",
            name="grace_period_duration",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Duration to defer the first future installment after the initial payment.",
            ),
        ),
        migrations.AddField(
            model_name="planfinancing",
            name="grace_period_duration_unit",
            field=models.CharField(
                choices=[("DAY", "Day"), ("WEEK", "Week"), ("MONTH", "Month"), ("YEAR", "Year")],
                default="MONTH",
                help_text="Unit used by grace_period_duration.",
                max_length=10,
            ),
        ),
    ]
