# Generated by Django 3.2.9 on 2021-12-14 17:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('certificate', '0014_merge_20210810_0418'),
    ]

    operations = [
        migrations.AddField(
            model_name='userspecialty',
            name='issued_at',
            field=models.DateTimeField(blank=True, default=None, null=True),
        ),
    ]
