from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0052_paymentmethod_qr_url"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlanFeatures",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "bullets",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='Checkout bullets by language, e.g. {"en": [{"title": "...", "description": "..."}], "es": [...]}',
                    ),
                ),
                (
                    "plan",
                    models.OneToOneField(
                        help_text="Plan these checkout bullets belong to",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="features",
                        to="payments.plan",
                    ),
                ),
            ],
        ),
    ]
