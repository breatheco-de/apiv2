# Generated by Django 3.2.16 on 2023-02-23 18:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registry", "0027_asset_github_commit_hash"),
    ]

    operations = [
        migrations.AlterField(
            model_name="asset",
            name="status",
            field=models.CharField(
                choices=[
                    ("UNASSIGNED", "Unassigned"),
                    ("WRITING", "Writing"),
                    ("DRAFT", "Draft"),
                    ("OPTIMIZED", "Optimized"),
                    ("PUBLISHED", "Published"),
                ],
                default="UNASSIGNED",
                help_text="Related to the publishing of the asset",
                max_length=20,
            ),
        ),
    ]
