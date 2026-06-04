from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("provisioning", "0004_provisioningacademy_vendor_settings"),
    ]

    operations = [
        migrations.AlterField(
            model_name="provisioningacademy",
            name="vendor_settings",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Vendor-specific allowlists/settings (for example: item_ids, template_ids, data_center_ids).",
            ),
        ),
    ]
