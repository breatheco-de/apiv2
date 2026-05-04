from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("authenticate", "0016_remove_githubacademyuser_copilot_granted"),
    ]

    operations = [
        migrations.AddField(
            model_name="userinvite",
            name="student_plan_access",
            field=models.JSONField(
                blank=True,
                default=None,
                help_text=(
                    "Financiamiento acordado al invitar estudiante (separado de conversion_info / UTMs). "
                    "Claves: how_many_installments, initial_payment_amount, initial_payment_notes, "
                    "grace_period_duration, grace_period_duration_unit."
                ),
                null=True,
            ),
        ),
    ]
