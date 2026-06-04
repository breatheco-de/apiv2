from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0047_invoice_notes_move_plan_financing_notes"),
        ("admissions", "0018_alter_cohort_cohorts_order"),
    ]

    operations = [
        migrations.AddField(
            model_name="academy",
            name="default_plan",
            field=models.ForeignKey(
                blank=True,
                help_text="Default checkout plan used when no plan is provided for this academy",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="default_for_academies",
                to="payments.plan",
            ),
        ),
    ]
