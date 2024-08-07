# Generated by Django 3.2.13 on 2022-07-01 19:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registry", "0008_auto_20220629_2026"),
    ]

    operations = [
        migrations.AddField(
            model_name="assetcategory",
            name="visibility",
            field=models.CharField(
                choices=[("PUBLIC", "Public"), ("UNLISTED", "Unlisted"), ("PRIVATE", "Private")],
                default="PUBLIC",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="assettechnology",
            name="lang",
            field=models.CharField(
                blank=True,
                default=None,
                help_text="Leave blank if will be shown in all languages",
                max_length=2,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="assettechnology",
            name="visibility",
            field=models.CharField(
                choices=[("PUBLIC", "Public"), ("UNLISTED", "Unlisted"), ("PRIVATE", "Private")],
                default="PUBLIC",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="keywordcluster",
            name="is_deprecated",
            field=models.BooleanField(
                default=False,
                help_text="Used when you want to stop using this cluster, all previous articles will be kept but no new articles will be assigned",
            ),
        ),
        migrations.AddField(
            model_name="keywordcluster",
            name="visibility",
            field=models.CharField(
                choices=[("PUBLIC", "Public"), ("UNLISTED", "Unlisted"), ("PRIVATE", "Private")],
                default="PUBLIC",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="asset",
            name="url",
            field=models.URLField(blank=True, default=None, null=True),
        ),
    ]
