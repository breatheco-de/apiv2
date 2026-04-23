from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("authenticate", "0014_add_academy_to_role"),
    ]

    operations = [
        migrations.AddField(
            model_name="githubacademyuser",
            name="copilot_granted",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="True when a GitHub Copilot seat has been explicitly granted/scheduled for this academy user row.",
            ),
        ),
    ]
