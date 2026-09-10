from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("marketing", "0018_formentry_crm_routing_audit"),
    ]

    operations = [
        migrations.AddField(
            model_name="crmconnection",
            name="mapping_fields",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    "Per-field value remaps for this connection. "
                    'Format: {"field": {"<lead-value>": "<mapping-value>"}}. '
                    "lead-value = value that arrives on the lead; "
                    "mapping-value = value sent to the CRM. "
                    'Example: {"tags": {"<lead-value>": "<mapping-value>"}}'
                ),
            ),
        ),
    ]
