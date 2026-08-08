from django.db import migrations, models


def backfill_installments_paid(apps, schema_editor):
    # Postgres-only UPDATE … AS alias; SQLite test DBs skip the data backfill.
    if schema_editor.connection.vendor != "postgresql":
        return

    schema_editor.execute(
        """
        UPDATE payments_planfinancing pf
        SET installments_paid = (
            SELECT CASE
                WHEN pf.initial_payment_amount IS NOT NULL
                    THEN GREATEST(COUNT(pi.invoice_id) - 1, 0)
                ELSE COUNT(pi.invoice_id)
            END
            FROM payments_planfinancing_invoices pi
            JOIN payments_bag b ON b.id = (
                SELECT bag_id FROM payments_invoice WHERE id = pi.invoice_id
            )
            WHERE pi.planfinancing_id = pf.id
              AND b.was_delivered = TRUE
        );
        """
    )


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0043_creditledgerentry"),
    ]

    operations = [
        migrations.AddField(
            model_name="planfinancing",
            name="installments_paid",
            field=models.PositiveIntegerField(
                default=0,
                help_text=(
                    "Number of billing cycles that have been fully closed, regardless of the payment method "
                    "(cash, Stripe, or internal credit). This is the single source of truth for installment "
                    "progress. plan_financing.invoices contains only real cash receipts."
                ),
            ),
        ),
        # Backfill: derive paid installments from existing invoice counts.
        # For plans with an initial_payment_amount (upfront + installments), the first invoice is the
        # initial deposit and does not count as a regular installment, so we subtract 1.
        migrations.RunPython(backfill_installments_paid, migrations.RunPython.noop),
    ]
