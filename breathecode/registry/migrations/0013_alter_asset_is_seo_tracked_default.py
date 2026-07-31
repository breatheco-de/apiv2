from django.db import migrations, models


def set_all_seo_tracked_false(apps, schema_editor):
    Asset = apps.get_model("registry", "Asset")
    Asset.objects.update(is_seo_tracked=False)


class Migration(migrations.Migration):

    dependencies = [
        ("registry", "0012_asseterrorlog_dedup_and_unique_constraints"),
    ]

    operations = [
        migrations.AlterField(
            model_name="asset",
            name="is_seo_tracked",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.RunPython(set_all_seo_tracked_false, migrations.RunPython.noop),
    ]
