import django.db.models.deletion
from django.db import migrations, models


def forwards_copy_plan_features_fk(apps, schema_editor):
    PlanFeatures = apps.get_model("payments", "PlanFeatures")
    Plan = apps.get_model("payments", "Plan")

    for plan_features in PlanFeatures.objects.all().iterator():
        plan_id = getattr(plan_features, "plan_id", None)
        if plan_id is None:
            continue
        Plan.objects.filter(id=plan_id).update(features_id=plan_features.id)


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0053_planfeatures"),
    ]

    operations = [
        migrations.AddField(
            model_name="plan",
            name="features",
            field=models.ForeignKey(
                blank=True,
                help_text="Shared checkout marketing bullets; multiple plans may reuse the same PlanFeatures",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="plans",
                to="payments.planfeatures",
            ),
        ),
        migrations.RunPython(forwards_copy_plan_features_fk, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="planfeatures",
            name="plan",
        ),
    ]
