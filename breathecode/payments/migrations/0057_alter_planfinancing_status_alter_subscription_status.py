# Generated by Django 5.1.7 on 2025-03-18 15:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0056_planfinancing_how_many_installments"),
    ]

    operations = [
        migrations.AlterField(
            model_name="planfinancing",
            name="status",
            field=models.CharField(
                choices=[
                    ("FREE_TRIAL", "Free trial"),
                    ("ACTIVE", "Active"),
                    ("CANCELLED", "Cancelled"),
                    ("DEPRECATED", "Deprecated"),
                    ("PAYMENT_ISSUE", "Payment issue"),
                    ("ERROR", "Error"),
                    ("FULLY_PAID", "Fully paid"),
                    ("EXPIRED", "Expired"),
                ],
                db_index=True,
                default="ACTIVE",
                help_text="Status",
                max_length=13,
            ),
        ),
        migrations.AlterField(
            model_name="subscription",
            name="status",
            field=models.CharField(
                choices=[
                    ("FREE_TRIAL", "Free trial"),
                    ("ACTIVE", "Active"),
                    ("CANCELLED", "Cancelled"),
                    ("DEPRECATED", "Deprecated"),
                    ("PAYMENT_ISSUE", "Payment issue"),
                    ("ERROR", "Error"),
                    ("FULLY_PAID", "Fully paid"),
                    ("EXPIRED", "Expired"),
                ],
                db_index=True,
                default="ACTIVE",
                help_text="Status",
                max_length=13,
            ),
        ),
    ]
