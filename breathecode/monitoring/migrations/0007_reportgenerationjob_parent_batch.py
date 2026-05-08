# Generated manually for parent/child report generation jobs

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("monitoring", "0006_reportgenerationjob"),
    ]

    operations = [
        migrations.AlterField(
            model_name="reportgenerationjob",
            name="academy",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="report_generation_jobs",
                to="admissions.academy",
            ),
        ),
        migrations.AddField(
            model_name="reportgenerationjob",
            name="batch_id",
            field=models.UUIDField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="reportgenerationjob",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="children",
                to="monitoring.reportgenerationjob",
            ),
        ),
        migrations.AddIndex(
            model_name="reportgenerationjob",
            index=models.Index(fields=["parent", "-created_at"], name="monitoring__parent_i_7c8a1e_idx"),
        ),
        migrations.AddIndex(
            model_name="reportgenerationjob",
            index=models.Index(fields=["batch_id"], name="monitoring__batch_i_d4e2b1_idx"),
        ),
    ]
