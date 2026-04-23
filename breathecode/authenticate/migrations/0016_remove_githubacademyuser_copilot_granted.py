from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("authenticate", "0015_githubacademyuser_copilot_granted"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="githubacademyuser",
            name="copilot_granted",
        ),
    ]
