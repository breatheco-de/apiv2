# Generated by Django 5.1.4 on 2024-12-09 20:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assignments", "0020_alter_userattachment_mime"),
    ]

    operations = [
        migrations.AlterField(
            model_name="repositorydeletionorder",
            name="repository_name",
            field=models.CharField(max_length=256),
        ),
        migrations.AlterField(
            model_name="repositorydeletionorder",
            name="repository_user",
            field=models.CharField(max_length=256),
        ),
        migrations.AlterField(
            model_name="repositorywhitelist",
            name="repository_name",
            field=models.CharField(max_length=256),
        ),
        migrations.AlterField(
            model_name="repositorywhitelist",
            name="repository_user",
            field=models.CharField(max_length=256),
        ),
    ]
