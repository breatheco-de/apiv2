from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0047_invoice_notes_move_plan_financing_notes"),
    ]

    operations = [
        migrations.AddField(
            model_name="planfinancing",
            name="last_status_change_at",
            field=models.DateTimeField(
                blank=True,
                default=None,
                help_text="When the status was last changed",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="subscription",
            name="last_status_change_at",
            field=models.DateTimeField(
                blank=True,
                default=None,
                help_text="When the status was last changed",
                null=True,
            ),
        ),
    ]
