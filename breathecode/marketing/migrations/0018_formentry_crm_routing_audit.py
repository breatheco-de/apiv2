import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("marketing", "0017_crm_routing_mvp"),
    ]

    operations = [
        migrations.AddField(
            model_name="formentry",
            name="crm_routing",
            field=models.ForeignKey(
                blank=True,
                default=None,
                help_text="CrmRouting rule applied when this lead was persisted (DROP or ROUTE)",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="form_entries",
                to="marketing.crmrouting",
            ),
        ),
        migrations.AddField(
            model_name="formentry",
            name="crm_routed_at",
            field=models.DateTimeField(
                blank=True,
                default=None,
                help_text="When CrmRouting was applied to this lead",
                null=True,
            ),
        ),
    ]
