# Generated by Django 3.1.7 on 2021-11-04 11:13

import django.db.models.manager
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("permissions", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelManagers(
            name="permissionmodel",
            managers=[
                ("all_objects", django.db.models.manager.Manager()),
            ],
        ),
    ]
