from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0009_merge_0007_luma_webhooks_0008_eventcheckin_phone"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventcheckin",
            name="first_name",
            field=models.CharField(blank=True, default=None, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="eventcheckin",
            name="last_name",
            field=models.CharField(blank=True, default=None, max_length=100, null=True),
        ),
    ]
