# Generated by Django 4.2 on 2023-05-10 11:41

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("flow", "0011_annotationpreset_contributor_correct_user"),
    ]

    operations = [
        migrations.AlterField(
            model_name="relation",
            name="category",
            field=models.CharField(max_length=100),
        ),
    ]