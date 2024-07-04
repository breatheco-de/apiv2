# Generated by Django 3.2.16 on 2022-12-27 20:39

from django.db import migrations, models

import breathecode.utils.validators.language


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0035_alter_eventtype_academy"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventtype",
            name="lang",
            field=models.CharField(
                default="en", max_length=5, validators=[breathecode.utils.validators.language.validate_language_code]
            ),
        ),
        migrations.AlterField(
            model_name="event",
            name="lang",
            field=models.CharField(
                blank=True,
                default=None,
                max_length=5,
                null=True,
                validators=[breathecode.utils.validators.language.validate_language_code],
            ),
        ),
    ]
