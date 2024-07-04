# Generated by Django 3.2.12 on 2022-04-08 20:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mentorship", "0012_alter_mentorshipsession_is_online"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mentorprofile",
            name="status",
            field=models.CharField(
                choices=[
                    ("INVITED", "Invited"),
                    ("ACTIVE", "Active"),
                    ("UNLISTED", "Unlisted"),
                    ("INNACTIVE", "Innactive"),
                ],
                default="INVITED",
                help_text="Options are: INVITEDACTIVEUNLISTEDINNACTIVE",
                max_length=15,
            ),
        ),
        migrations.AlterField(
            model_name="mentorshipservice",
            name="status",
            field=models.CharField(
                choices=[
                    ("DRAFT", "Draft"),
                    ("ACTIVE", "Active"),
                    ("UNLISTED", "Unlisted"),
                    ("INNACTIVE", "Innactive"),
                ],
                default="DRAFT",
                max_length=15,
            ),
        ),
    ]
