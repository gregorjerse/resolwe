# Generated by Django 4.2.6 on 2023-10-27 07:52

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("flow", "0017_collectionhistory_datahistory_sizechange_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="annotationvalue",
            options={"ordering": ["field__group__sort_order", "field__sort_order"]},
        ),
    ]
