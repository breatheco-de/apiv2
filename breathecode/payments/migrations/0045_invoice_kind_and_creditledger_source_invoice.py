from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0044_planfinancing_installments_paid"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoice",
            name="invoice_kind",
            field=models.CharField(
                choices=[("GENERAL", "General"), ("MANUAL_DEPOSIT", "Manual deposit")],
                db_index=True,
                default="GENERAL",
                help_text="Business origin/classification for this invoice",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="creditledgerentry",
            name="source_invoice",
            field=models.ForeignKey(
                blank=True,
                default=None,
                help_text="Invoice that originated this credit movement (manual deposits, automatic adjustments, etc.)",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="credit_entries",
                to="payments.invoice",
            ),
        ),
    ]
