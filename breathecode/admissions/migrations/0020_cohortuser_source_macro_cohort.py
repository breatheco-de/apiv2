import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("admissions", "0019_academy_default_plan"),
    ]

    operations = [
        migrations.AddField(
            model_name="cohortuser",
            name="source_macro_cohort",
            field=models.ForeignKey(
                blank=True,
                default=None,
                help_text="Macro cohort this micro enrollment was created from. Null means legacy or ambiguous.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="sourced_micro_cohort_users",
                to="admissions.cohort",
            ),
        ),
    ]
