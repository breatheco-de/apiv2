# Generated manually

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("commission", "0003_remove_teacherinfluencerreferralcommission_matured_at_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="teacherinfluencerreferralcommission",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now, editable=True),
        ),
    ]
