from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0045_invoice_kind_and_creditledger_source_invoice"),
    ]

    operations = [
        # Backfill ledger source_invoice from legacy source_deposit links before dropping them.
        migrations.RunSQL(
            sql="""
                UPDATE payments_creditledgerentry cle
                SET source_invoice_id = sd.invoice_id
                FROM payments_studentdeposit sd
                WHERE cle.source_invoice_id IS NULL
                  AND cle.source_deposit_id = sd.id;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RemoveField(
            model_name="creditledgerentry",
            name="source_deposit",
        ),
        migrations.DeleteModel(
            name="StudentDeposit",
        ),
    ]
