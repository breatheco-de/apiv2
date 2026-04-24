from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registry", "0010_asset_github_activity_log"),
    ]

    operations = [
        migrations.AddField(
            model_name="asseterrorlog",
            name="priority",
            field=models.SmallIntegerField(default=False),
        ),
    ]
