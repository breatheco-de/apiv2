from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assignments", "0003_learnpackwebhook_asset_package_ids"),
    ]

    operations = [
        migrations.AddField(
            model_name="learnpackwebhook",
            name="package_slug",
            field=models.SlugField(blank=True, db_index=True, max_length=200, null=True),
        ),
    ]
