# Generated by Django 5.1.1 on 2024-10-01 02:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("authenticate", "0057_credentialsgoogle_id_token"),
    ]

    operations = [
        migrations.AddField(
            model_name="credentialsgoogle",
            name="google_id",
            field=models.CharField(default="", max_length=24),
        ),
    ]
