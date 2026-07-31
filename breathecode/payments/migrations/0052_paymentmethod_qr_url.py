from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0051_alter_service_consumer"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymentmethod",
            name="qr_url",
            field=models.URLField(
                blank=True,
                default=None,
                help_text="Public HTTPS URL of a QR image to display at the bottom of this payment method in checkout",
                null=True,
            ),
        ),
    ]
