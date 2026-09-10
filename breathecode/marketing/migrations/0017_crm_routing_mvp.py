import json

import django.db.models.deletion
from django.db import migrations, models


def migrate_crm_lead_overrides(apps, schema_editor):
    CRMConnection = apps.get_model("marketing", "CRMConnection")
    CrmRouting = apps.get_model("marketing", "CrmRouting")

    for routing in CrmRouting.objects.all():
        value = json.dumps((routing.match_value or "").strip().lower())
        routing.condition = f"lead.{routing.match_field} == {value}"

        has_destination = bool(
            routing.destination_ac_url and routing.destination_ac_key and routing.destination_crm_vendor
        )
        if has_destination:
            connection, _ = CRMConnection.objects.get_or_create(
                crm_vendor=routing.destination_crm_vendor,
                api_url=routing.destination_ac_url if routing.destination_crm_vendor == "ACTIVE_CAMPAIGN" else None,
                api_key=routing.destination_ac_key,
                defaults={
                    "name": f"Migrated CRM routing {routing.pk}",
                    "sync_status": "INCOMPLETED",
                    "sync_message": "Migrated from CrmLeadOverride; connection must be tested",
                },
            )
            routing.action = "ROUTE"
            routing.connection = connection
        else:
            routing.action = "DROP"
            routing.connection = None

        routing.save(update_fields=["condition", "action", "connection"])


class Migration(migrations.Migration):

    dependencies = [
        ("marketing", "0016_crmleadoverride"),
    ]

    operations = [
        migrations.CreateModel(
            name="CRMConnection",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
                (
                    "crm_vendor",
                    models.CharField(
                        choices=[("ACTIVE_CAMPAIGN", "Active Campaign"), ("BREVO", "Brevo")], max_length=20
                    ),
                ),
                ("api_url", models.URLField(blank=True, default=None, null=True)),
                ("api_key", models.CharField(max_length=150)),
                (
                    "sync_status",
                    models.CharField(
                        choices=[("INCOMPLETED", "Incompleted"), ("COMPLETED", "Completed")],
                        default="INCOMPLETED",
                        max_length=15,
                    ),
                ),
                ("sync_message", models.CharField(blank=True, default=None, max_length=255, null=True)),
                ("last_interaction_at", models.DateTimeField(blank=True, default=None, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.RenameModel(
            old_name="CrmLeadOverride",
            new_name="CrmRouting",
        ),
        migrations.RemoveConstraint(
            model_name="crmrouting",
            name="uniq_crm_lead_override_match",
        ),
        migrations.RemoveConstraint(
            model_name="crmrouting",
            name="crm_lead_override_destination_all_or_nothing",
        ),
        migrations.AddField(
            model_name="crmrouting",
            name="action",
            field=models.CharField(choices=[("ROUTE", "Route"), ("DROP", "Drop")], default="ROUTE", max_length=10),
        ),
        migrations.AddField(
            model_name="crmrouting",
            name="condition",
            field=models.TextField(
                blank=True,
                default="",
                help_text='CEL expression evaluated against FormEntry as "lead". Empty matches every lead.',
            ),
        ),
        migrations.AddField(
            model_name="crmrouting",
            name="connection",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="routes",
                to="marketing.crmconnection",
            ),
        ),
        migrations.RunPython(migrate_crm_lead_overrides, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="crmrouting",
            name="destination_ac_key",
        ),
        migrations.RemoveField(
            model_name="crmrouting",
            name="destination_ac_url",
        ),
        migrations.RemoveField(
            model_name="crmrouting",
            name="destination_crm_vendor",
        ),
        migrations.RemoveField(
            model_name="crmrouting",
            name="match_field",
        ),
        migrations.RemoveField(
            model_name="crmrouting",
            name="match_value",
        ),
        migrations.AddConstraint(
            model_name="crmrouting",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(("action", "ROUTE"), ("connection__isnull", False))
                    | models.Q(("action", "DROP"), ("connection__isnull", True))
                ),
                name="crm_routing_action_connection",
            ),
        ),
    ]
