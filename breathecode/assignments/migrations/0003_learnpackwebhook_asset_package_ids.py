from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assignments", "0002_task_delivered_flags"),
    ]

    operations = [
        migrations.AddField(
            model_name="learnpackwebhook",
            name="asset_id",
            field=models.BigIntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="learnpackwebhook",
            name="learnpack_package_id",
            field=models.BigIntegerField(blank=True, db_index=True, null=True),
        ),
    ]
