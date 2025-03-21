# Generated by Django 5.1.4 on 2025-01-07 20:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("authenticate", "0062_delete_app"),
    ]

    operations = [
        migrations.CreateModel(
            name="App",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "name",
                    models.CharField(help_text="Descriptive and unique name of the app", max_length=25, unique=True),
                ),
            ],
        ),
    ]
