from django.db import migrations, models
from django.db.models import Count, Min, Q


STATUS_PRIORITY = {"ERROR": 3, "FIXED": 2, "IGNORED": 1}


def deduplicate_asset_error_logs(apps, schema_editor):
    AssetErrorLog = apps.get_model("registry", "AssetErrorLog")

    groups = (
        AssetErrorLog.objects.values("slug", "asset_type", "path", "asset_id")
        .annotate(total=Count("id"), keeper_id=Min("id"))
        .filter(total__gt=1)
    )

    for group in groups.iterator():
        duplicate_rows = list(
            AssetErrorLog.objects.filter(
                slug=group["slug"],
                asset_type=group["asset_type"],
                path=group["path"],
                asset_id=group["asset_id"],
            ).order_by("id")
        )

        if len(duplicate_rows) <= 1:
            continue

        keeper = duplicate_rows[0]
        status = max((row.status for row in duplicate_rows), key=lambda x: STATUS_PRIORITY.get(x, 0))

        status_text = None
        for row in reversed(duplicate_rows):
            if row.status_text:
                status_text = row.status_text
                break

        user_id = None
        for row in reversed(duplicate_rows):
            if row.user_id:
                user_id = row.user_id
                break

        update_fields = []
        if keeper.status != status:
            keeper.status = status
            update_fields.append("status")

        if keeper.status_text != status_text:
            keeper.status_text = status_text
            update_fields.append("status_text")

        if keeper.user_id != user_id:
            keeper.user_id = user_id
            update_fields.append("user")

        if update_fields:
            keeper.save(update_fields=update_fields)

        duplicate_ids = [row.id for row in duplicate_rows[1:]]
        if duplicate_ids:
            AssetErrorLog.objects.filter(id__in=duplicate_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("registry", "0011_asseterrorlog_priority"),
    ]

    operations = [
        migrations.RunPython(deduplicate_asset_error_logs, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="asseterrorlog",
            constraint=models.UniqueConstraint(
                condition=Q(asset__isnull=False),
                fields=("slug", "asset_type", "path", "asset"),
                name="uniq_asset_error_log_with_asset",
            ),
        ),
        migrations.AddConstraint(
            model_name="asseterrorlog",
            constraint=models.UniqueConstraint(
                condition=Q(asset__isnull=True),
                fields=("slug", "asset_type", "path"),
                name="uniq_asset_error_log_without_asset",
            ),
        ),
    ]
