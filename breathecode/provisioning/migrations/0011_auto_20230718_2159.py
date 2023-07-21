# Generated by Django 3.2.19 on 2023-07-18 21:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('provisioning', '0010_provisioninguserconsumption_quantity'),
    ]

    operations = [
        migrations.AlterField(
            model_name='provisioninguserconsumption',
            name='events',
            field=models.ManyToManyField(blank=True,
                                         editable=False,
                                         to='provisioning.ProvisioningConsumptionEvent'),
        ),
        migrations.DeleteModel(name='ProvisioningActivity', ),
    ]