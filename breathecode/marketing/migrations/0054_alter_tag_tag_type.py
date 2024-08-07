# Generated by Django 3.2.9 on 2022-02-23 19:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("marketing", "0053_tag_description"),
    ]

    operations = [
        migrations.AlterField(
            model_name="tag",
            name="tag_type",
            field=models.CharField(
                choices=[
                    ("STRONG", "Strong"),
                    ("SOFT", "Soft"),
                    ("DISCOVERY", "Discovery"),
                    ("COHORT", "Cohort"),
                    ("DOWNLOADABLE", "Downloadable"),
                    ("EVENT", "Event"),
                    ("OTHER", "Other"),
                ],
                default=None,
                help_text="The STRONG tags in a lead will determine to witch automation it does unless there is an 'automation' property on the lead JSON",
                max_length=15,
                null=True,
            ),
        ),
    ]
