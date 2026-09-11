from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("admissions", "0020_cohortuser_source_macro_cohort"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cohort",
            name="cohorts_order",
            field=models.CharField(
                blank=True,
                default=None,
                help_text="Comma-separated micro cohort IDs in display order. "
                "Sized for ~40 five-digit IDs plus commas/spaces (and extra headroom).",
                max_length=3000,
                null=True,
            ),
        ),
    ]
