from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0007_eventcheckin_utm_location"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventcheckin",
            name="phone",
            field=models.CharField(blank=True, default=None, max_length=17, null=True),
        ),
    ]
