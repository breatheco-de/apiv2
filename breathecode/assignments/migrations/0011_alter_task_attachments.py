# Generated by Django 3.2.16 on 2022-10-26 04:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assignments", "0010_auto_20221026_0340"),
    ]

    operations = [
        migrations.AlterField(
            model_name="task",
            name="attachments",
            field=models.ManyToManyField(blank=True, to="assignments.UserAttachment"),
        ),
    ]
