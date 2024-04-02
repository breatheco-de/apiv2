# Generated by Django 3.2.23 on 2023-11-23 16:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registry', '0037_auto_20231110_1847'),
    ]

    operations = [
        migrations.AlterField(
            model_name='asset',
            name='status',
            field=models.CharField(choices=[('NOT_STARTED', 'Not Started'), ('PLANNING', 'Planning'),
                                            ('WRITING', 'Writing'), ('DRAFT', 'Draft'), ('OPTIMIZED', 'Optimized'),
                                            ('PUBLISHED', 'Published')],
                                   db_index=True,
                                   default='NOT_STARTED',
                                   help_text="It won't be shown on the website until the status is published",
                                   max_length=20),
        ),
        migrations.AlterField(
            model_name='asset',
            name='visibility',
            field=models.CharField(
                choices=[('PUBLIC', 'Public'), ('UNLISTED', 'Unlisted'), ('PRIVATE', 'Private')],
                db_index=True,
                default='PUBLIC',
                help_text=
                "This is an internal property. It won't be shown internally to other academies unless is public",
                max_length=20),
        ),
    ]
