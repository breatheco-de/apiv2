# Generated by Django 3.1.4 on 2020-12-30 22:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0018_eventticket"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventcheckin",
            name="status",
            field=models.CharField(choices=[("PENDING", "Pending"), ("DONE", "Done")], default="PENDING", max_length=9),
        ),
        migrations.DeleteModel(
            name="EventTicket",
        ),
    ]
