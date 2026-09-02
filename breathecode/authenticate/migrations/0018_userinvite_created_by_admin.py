from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("authenticate", "0017_userinvite_student_plan_access"),
    ]

    operations = [
        migrations.AddField(
            model_name="userinvite",
            name="created_by_admin",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text=(
                    "When True, accepting this invite creates the PlanFinancing with created_by_admin=True. "
                    "Set it on academy/staff invites; leave False for self-serve or other invite sources."
                ),
            ),
        ),
    ]
