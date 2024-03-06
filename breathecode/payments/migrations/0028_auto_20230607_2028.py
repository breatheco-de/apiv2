# Generated by Django 3.2.19 on 2023-06-07 20:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0027_merge_0026_auto_20230502_2225_0026_plan_invites'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='service',
            name='currency',
        ),
        migrations.RemoveField(
            model_name='service',
            name='price_per_unit',
        ),
        migrations.AlterField(
            model_name='academyservice',
            name='max_items',
            field=models.FloatField(
                default=1, help_text="How many items can be bought in total, it doesn't matter the bundle size"),
        ),
    ]
