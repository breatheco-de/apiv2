from django.db import migrations, models


def move_plan_financing_notes_to_first_invoice(apps, schema_editor):
    PlanFinancing = apps.get_model("payments", "PlanFinancing")
    db_alias = schema_editor.connection.alias

    qs = (
        PlanFinancing.objects.using(db_alias)
        .exclude(initial_payment_notes__isnull=True)
        .exclude(initial_payment_notes="")
    )
    for financing in qs.iterator():
        first_invoice = financing.invoices.order_by("paid_at", "id").first()
        if first_invoice is None:
            continue

        first_invoice.invoice_notes = financing.initial_payment_notes
        first_invoice.save(using=db_alias, update_fields=["invoice_notes"])


def move_invoice_notes_back_to_plan_financing(apps, schema_editor):
    PlanFinancing = apps.get_model("payments", "PlanFinancing")
    db_alias = schema_editor.connection.alias

    qs = PlanFinancing.objects.using(db_alias).filter(initial_payment_notes__isnull=True)
    for financing in qs.iterator():
        first_invoice = financing.invoices.order_by("paid_at", "id").first()
        if first_invoice is None or not first_invoice.invoice_notes:
            continue

        financing.initial_payment_notes = first_invoice.invoice_notes[:250]
        financing.save(using=db_alias, update_fields=["initial_payment_notes"])


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0046_remove_studentdeposit_and_legacy_source_deposit"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoice",
            name="invoice_notes",
            field=models.TextField(
                blank=True,
                default=None,
                help_text="Staff notes or payment context associated with this invoice.",
                null=True,
            ),
        ),
        migrations.RunPython(
            move_plan_financing_notes_to_first_invoice,
            reverse_code=move_invoice_notes_back_to_plan_financing,
        ),
        migrations.RemoveField(
            model_name="planfinancing",
            name="initial_payment_notes",
        ),
    ]
