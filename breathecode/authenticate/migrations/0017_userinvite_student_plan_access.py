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
                    "Agreed-on financing when inviting a student (kept separate from conversion_info / UTMs). "
                    "Keys: how_many_installments, initial_payment_amount, initial_payment_notes, "
                    "grace_period_duration, grace_period_duration_unit."
                ),
                null=True,
            ),
        ),
    ]
