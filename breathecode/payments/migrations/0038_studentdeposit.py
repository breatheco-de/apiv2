from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("admissions", "0017_academy_short_url"),
        ("payments", "0037_planfinancing_initial_payment_and_grace"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StudentDeposit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.FloatField(help_text="Deposit amount")),
                (
                    "status",
                    models.CharField(
                        choices=[("HELD", "Held"), ("APPLIED", "Applied"), ("REFUNDED", "Refunded")],
                        db_index=True,
                        default="HELD",
                        help_text="Deposit status",
                        max_length=8,
                    ),
                ),
                (
                    "notes",
                    models.CharField(
                        blank=True,
                        default=None,
                        help_text="Optional staff notes about this deposit",
                        max_length=250,
                        null=True,
                    ),
                ),
                (
                    "applied_at",
                    models.DateTimeField(blank=True, default=None, help_text="When the deposit was applied", null=True),
                ),
                (
                    "refunded_at",
                    models.DateTimeField(blank=True, default=None, help_text="When the deposit was refunded", null=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True, editable=False)),
                (
                    "academy",
                    models.ForeignKey(
                        help_text="Academy that received the deposit",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="admissions.academy",
                    ),
                ),
                (
                    "currency",
                    models.ForeignKey(
                        help_text="Deposit currency",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="payments.currency",
                    ),
                ),
                (
                    "invoice",
                    models.OneToOneField(
                        help_text="Invoice that records this deposit payment",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="student_deposit",
                        to="payments.invoice",
                    ),
                ),
                (
                    "plan_financing",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        help_text="Plan financing where this deposit was applied",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="student_deposits",
                        to="payments.planfinancing",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        help_text="Student who made the deposit",
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
