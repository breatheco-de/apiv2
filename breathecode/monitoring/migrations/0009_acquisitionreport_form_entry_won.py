# FORM_ENTRY_WON source type for wins keyed to won_at date

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("monitoring", "0008_acquisitionreport_event_sources"),
    ]

    operations = [
        migrations.AlterField(
            model_name="acquisitionreport",
            name="source_type",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("FORM_ENTRY", "Form entry"),
                    ("FORM_ENTRY_WON", "Form entry (won)"),
                    ("USER_INVITE", "User invite"),
                    ("EVENT_RSVP", "Event RSVP"),
                    ("EVENT_ATTENDED", "Event attended"),
                ],
            ),
        ),
    ]
