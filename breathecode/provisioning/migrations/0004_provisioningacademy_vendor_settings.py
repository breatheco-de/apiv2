from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("provisioning", "0003_add_provisioning_vps_deleted_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="provisioningacademy",
            name="vendor_settings",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
