from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0006_academyeventsettings"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventcheckin",
            name="utm_location",
            field=models.CharField(blank=True, default=None, max_length=70, null=True),
        ),
    ]
