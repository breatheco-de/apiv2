from django.db import migrations, models


def clear_time_of_life_on_renewable_plans(apps, schema_editor):
    Plan = apps.get_model("payments", "Plan")

    for plan in Plan.objects.filter(is_renewable=True).iterator():
        has_price = any(
            [
                plan.price_per_month,
                plan.price_per_year,
                plan.price_per_quarter,
                plan.price_per_half,
            ]
        )
        if has_price or plan.trial_duration:
            Plan.objects.filter(pk=plan.pk).update(time_of_life=None, time_of_life_unit=None)


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0048_subscription_last_status_change_at"),
    ]

    operations = [
        migrations.RunPython(clear_time_of_life_on_renewable_plans, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="plan",
            name="time_of_life",
            field=models.IntegerField(
                blank=True,
                help_text="Plan lifetime (e.g. 1, 2, 3, ...)",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="plan",
            name="time_of_life_unit",
            field=models.CharField(
                blank=True,
                choices=[
                    ("DAY", "Day"),
                    ("WEEK", "Week"),
                    ("MONTH", "Month"),
                    ("YEAR", "Year"),
                ],
                help_text="Lifetime unit (e.g. DAY, WEEK, MONTH or YEAR)",
                max_length=10,
                null=True,
            ),
        ),
    ]
