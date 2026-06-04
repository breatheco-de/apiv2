# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0029_service_is_model_service"),
    ]

    operations = [
        migrations.AddField(
            model_name="academypaymentsettings",
            name="feature_flags",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Feature flags and configuration settings for academy-specific features",
            ),
        ),
        migrations.AddField(
            model_name="coupon",
            name="times_used",
            field=models.IntegerField(
                db_index=True, default=0, help_text="Number of times this coupon has been used"
            ),
        ),
        migrations.AddField(
            model_name="coupon",
            name="last_used_at",
            field=models.DateTimeField(
                blank=True, db_index=True, help_text="When this coupon was last used", null=True
            ),
        ),
        migrations.AddField(
            model_name="coupon",
            name="stats",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Detailed statistics (only calculated for recently active coupons)",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="coupon",
            name="stats_updated_at",
            field=models.DateTimeField(blank=True, help_text="When stats were last calculated", null=True),
        ),
    ]

