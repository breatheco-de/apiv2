from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0038_studentdeposit"),
    ]

    operations = [
        migrations.AddField(
            model_name="plan",
            name="discontinued_reason",
            field=models.TextField(
                blank=True,
                help_text="Required when transitioning the plan status to DISCONTINUED",
                null=True,
            ),
        ),
    ]
