from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0055_active_users_bill_and_internal_billing"),
    ]

    operations = [
        migrations.AddField(
            model_name="planfinancing",
            name="created_by_admin",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text=(
                    "True when staff created this financing (academy POST, invite, or backfill of "
                    "plans that had at least one invoice with proof of payment). Runtime logic must "
                    "not infer this from invoice proofs."
                ),
            ),
        ),
    ]
