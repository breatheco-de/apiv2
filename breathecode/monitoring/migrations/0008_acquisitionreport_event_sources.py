# Event RSVP / attended source types on AcquisitionReport

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("monitoring", "0007_reportgenerationjob_parent_batch"),
    ]

    operations = [
        migrations.AlterField(
            model_name="acquisitionreport",
            name="source_type",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("FORM_ENTRY", "Form entry"),
                    ("USER_INVITE", "User invite"),
                    ("EVENT_RSVP", "Event RSVP"),
                    ("EVENT_ATTENDED", "Event attended"),
                ],
            ),
        ),
    ]
