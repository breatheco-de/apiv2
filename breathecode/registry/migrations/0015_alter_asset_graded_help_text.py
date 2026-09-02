from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registry", "0014_merge_20260731_1825"),
    ]

    operations = [
        migrations.AlterField(
            model_name="asset",
            name="graded",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="Deprecated. All assets are graded with AI. Do not use this flag to enable grading or telemetry.",
            ),
        ),
    ]
