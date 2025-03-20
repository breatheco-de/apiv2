from django.db import migrations, models


def migrate_syllabus_data(apps, schema_editor):
    Specialty = apps.get_model("certificate", "Specialty")

    for specialty in Specialty.objects.all():
        if specialty.syllabus_id:
            specialty.syllabus.add(specialty.syllabus_id)


class Migration(migrations.Migration):

    dependencies = [
        ("admissions", "0068_merge_20241216_1552"),
        ("certificate", "0017_layoutdesign_foot_note"),
    ]

    operations = [
        migrations.AddField(
            model_name="specialty",
            name="syllabus_m2m",
            field=models.ManyToManyField(
                blank=True, help_text="This specialty can be earned from multiple courses", to="admissions.syllabus"
            ),
        ),
        migrations.RunPython(migrate_syllabus_data),
        migrations.RemoveField(
            model_name="specialty",
            name="syllabus",
        ),
        migrations.RenameField(
            model_name="specialty",
            old_name="syllabus_m2m",
            new_name="syllabus",
        ),
    ]
