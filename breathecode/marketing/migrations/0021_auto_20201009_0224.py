# Generated by Django 3.1.1 on 2020-10-09 02:24

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("marketing", "0020_formentry_gclid"),
    ]

    operations = [
        migrations.AddField(
            model_name="formentry",
            name="browser_lang",
            field=models.CharField(blank=True, default=None, max_length=5, null=True),
        ),
        migrations.AlterField(
            model_name="formentry",
            name="city",
            field=models.CharField(blank=True, default=None, max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name="formentry",
            name="contact",
            field=models.ForeignKey(
                blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to="marketing.contact"
            ),
        ),
        migrations.AlterField(
            model_name="formentry",
            name="country",
            field=models.CharField(blank=True, default=None, max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name="formentry",
            name="latitude",
            field=models.DecimalField(blank=True, decimal_places=6, default=None, max_digits=9, null=True),
        ),
        migrations.AlterField(
            model_name="formentry",
            name="longitude",
            field=models.DecimalField(blank=True, decimal_places=6, default=None, max_digits=9, null=True),
        ),
        migrations.AlterField(
            model_name="formentry",
            name="state",
            field=models.CharField(blank=True, default=None, max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name="formentry",
            name="street_address",
            field=models.CharField(blank=True, default=None, max_length=250, null=True),
        ),
        migrations.AlterField(
            model_name="formentry",
            name="zip_code",
            field=models.IntegerField(blank=True, default=None, null=True),
        ),
    ]
