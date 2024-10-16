# Generated by Django 3.1.7 on 2021-10-12 10:39
from django.db import migrations, models


def create_duplicate_dependencies(apps, schema_editor):
    Data = apps.get_model("flow", "Data")
    DataDependency = apps.get_model("flow", "DataDependency")
    duplicates = Data.objects.filter(duplicated__isnull=False)
    duplicates_without_relation = duplicates.exclude(
        parents_dependency__kind="duplicate"
    ).annotate(
        parent_id=models.Subquery(
            Data.objects.filter(
                location_id=models.OuterRef("location_id"), duplicated__isnull=True
            ).values("id")
        )
    )
    DataDependency.objects.bulk_create(
        DataDependency(kind="duplicate", parent_id=duplicate.parent_id, child=duplicate)
        for duplicate in duplicates_without_relation
    )


class Migration(migrations.Migration):

    dependencies = [
        ("flow", "0004_data_process_resources"),
    ]

    operations = [
        migrations.RunPython(create_duplicate_dependencies),
    ]
