# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-06-26 04:31
from __future__ import unicode_literals

from django.conf import settings
import django.contrib.postgres.fields
import django.contrib.postgres.fields.jsonb
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import versionfield
import resolwe.flow.models.fields


class Migration(migrations.Migration):

    replaces = [
        ('flow', '0001_initial'),
        ('flow', '0002_project_to_collection'),
        ('flow', '0003_support_sample'),
        ('flow', '0004_autoslug_field'),
        ('flow', '0005_process_data_name'),
        ('flow', '0006_data_named_by_user'),
        ('flow', '0007_add_owner'),
        ('flow', '0008_fix_jsonfields'),
        ('flow', '0009_data_parents'),
        ('flow', '0010_fix_jsonfields'),
        ('flow', '0011_calculate_checksum'),
        ('flow', '0012_require_checksum'),
        ('flow', '0013_add_requirements'),
        ('flow', '0014_add_entity'),
        ('flow', '0015_make_data_indexes'),
        ('flow', '0016_update_versionfield'),
        ('flow', '0017_update_checksum'),
        ('flow', '0018_remove_triggers'),
        ('flow', '0019_data_descriptor_dirty'),
        ('flow', '0020_collection_descriptor_dirty'),
        ('flow', '0021_entity_descriptor_completed'),
        ('flow', '0022_data_sha1_to_sha256'),
        ('flow', '0023_update_checksum'),
        ('flow', '0024_add_relations'),
        ('flow', '0025_set_get_last_by'),
        ('flow', '0026_tags'),
        ('flow', '0027_scheduling_class'),
        ('flow', '0028_remove_public_processes'),
        ('flow', '0029_data_checksum_index'),
        ('flow', '0030_change_slug_field')
    ]

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Collection',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', resolwe.flow.models.fields.ResolweSlugField(max_length=100, populate_from='name', unique_with=('version',))),
                ('version', versionfield.VersionField(default='0.0.0')),
                ('name', models.CharField(max_length=100)),
                ('created', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('modified', models.DateTimeField(auto_now=True, db_index=True)),
                ('description', models.TextField(blank=True)),
                ('settings', django.contrib.postgres.fields.jsonb.JSONField(default=dict)),
                ('descriptor', django.contrib.postgres.fields.jsonb.JSONField(default=dict)),
                ('descriptor_dirty', models.BooleanField(default=False)),
                ('contributor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'permissions': (('view_collection', 'Can view collection'), ('edit_collection', 'Can edit collection'), ('share_collection', 'Can share collection'), ('download_collection', 'Can download files from collection'), ('add_collection', 'Can add data objects to collection'), ('owner_collection', 'Is owner of the collection')),
                'get_latest_by': 'version',
                'abstract': False,
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='Data',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', resolwe.flow.models.fields.ResolweSlugField(max_length=100, populate_from='name', unique_with=('version',))),
                ('version', versionfield.VersionField(default='0.0.0')),
                ('name', models.CharField(max_length=100)),
                ('created', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('modified', models.DateTimeField(auto_now=True, db_index=True)),
                ('started', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('finished', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('checksum', models.CharField(db_index=True, max_length=64, validators=[django.core.validators.RegexValidator(code='invalid_checksum', message='Checksum is exactly 40 alphanumerics', regex='^[0-9a-f]{64}$')])),
                ('status', models.CharField(choices=[('UP', 'Uploading'), ('RE', 'Resolving'), ('WT', 'Waiting'), ('PR', 'Processing'), ('OK', 'Done'), ('ER', 'Error'), ('DR', 'Dirty')], default='RE', max_length=2)),
                ('process_pid', models.PositiveIntegerField(blank=True, null=True)),
                ('process_progress', models.PositiveSmallIntegerField(default=0)),
                ('process_rc', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('process_info', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), default=[], size=None)),
                ('process_warning', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), default=[], size=None)),
                ('process_error', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), default=[], size=None)),
                ('input', django.contrib.postgres.fields.jsonb.JSONField(default=dict)),
                ('output', django.contrib.postgres.fields.jsonb.JSONField(default=dict)),
                ('descriptor', django.contrib.postgres.fields.jsonb.JSONField(default=dict)),
                ('descriptor_dirty', models.BooleanField(default=False)),
                ('named_by_user', models.BooleanField(default=False)),
                ('tags', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), default=list, size=None)),
                ('contributor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'permissions': (('view_data', 'Can view data'), ('edit_data', 'Can edit data'), ('share_data', 'Can share data'), ('download_data', 'Can download files from data'), ('owner_data', 'Is owner of the data')),
                'get_latest_by': 'version',
                'abstract': False,
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='DescriptorSchema',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', resolwe.flow.models.fields.ResolweSlugField(max_length=100, populate_from='name', unique_with=('version',))),
                ('version', versionfield.VersionField(default='0.0.0')),
                ('name', models.CharField(max_length=100)),
                ('created', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('modified', models.DateTimeField(auto_now=True, db_index=True)),
                ('description', models.TextField(blank=True)),
                ('schema', django.contrib.postgres.fields.jsonb.JSONField(default=list)),
                ('contributor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'permissions': (('view_descriptorschema', 'Can view descriptor schema'), ('edit_descriptorschema', 'Can edit descriptor schema'), ('share_descriptorschema', 'Can share descriptor schema'), ('owner_descriptorschema', 'Is owner of the description schema')),
                'get_latest_by': 'version',
                'abstract': False,
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='Entity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', resolwe.flow.models.fields.ResolweSlugField(max_length=100, populate_from='name', unique_with=('version',))),
                ('version', versionfield.VersionField(default='0.0.0')),
                ('name', models.CharField(max_length=100)),
                ('created', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('modified', models.DateTimeField(auto_now=True, db_index=True)),
                ('description', models.TextField(blank=True)),
                ('settings', django.contrib.postgres.fields.jsonb.JSONField(default=dict)),
                ('descriptor', django.contrib.postgres.fields.jsonb.JSONField(default=dict)),
                ('descriptor_dirty', models.BooleanField(default=False)),
                ('descriptor_completed', models.BooleanField(default=False)),
                ('tags', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), default=list, size=None)),
                ('collections', models.ManyToManyField(to='flow.Collection')),
                ('contributor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('data', models.ManyToManyField(to='flow.Data')),
                ('descriptor_schema', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='flow.DescriptorSchema')),
            ],
            options={
                'permissions': (('view_entity', 'Can view entity'), ('edit_entity', 'Can edit entity'), ('share_entity', 'Can share entity'), ('download_entity', 'Can download files from entity'), ('add_entity', 'Can add data objects to entity'), ('owner_entity', 'Is owner of the entity')),
                'get_latest_by': 'version',
                'abstract': False,
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='PositionInRelation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('entity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='flow.Entity')),
            ],
        ),
        migrations.CreateModel(
            name='Process',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', resolwe.flow.models.fields.ResolweSlugField(max_length=100, populate_from='name', unique_with=('version',))),
                ('version', versionfield.VersionField(default='0.0.0')),
                ('name', models.CharField(max_length=100)),
                ('created', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('modified', models.DateTimeField(auto_now=True, db_index=True)),
                ('type', models.CharField(max_length=100, validators=[django.core.validators.RegexValidator(code='invalid_type', message='Type may be alphanumerics separated by colon', regex='^data:[a-z0-9:]+:$')])),
                ('category', models.CharField(default='other', max_length=200, validators=[django.core.validators.RegexValidator(code='invalid_category', message='Category may be alphanumerics separated by colon', regex='^([a-z0-9]+[:\\-])*[a-z0-9]+:$')])),
                ('persistence', models.CharField(choices=[('RAW', 'Raw'), ('CAC', 'Cached'), ('TMP', 'Temp')], default='RAW', max_length=3)),
                ('description', models.TextField(default='')),
                ('data_name', models.CharField(blank=True, max_length=200, null=True)),
                ('input_schema', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=list)),
                ('output_schema', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=list)),
                ('flow_collection', models.CharField(blank=True, max_length=100, null=True)),
                ('run', django.contrib.postgres.fields.jsonb.JSONField(default=dict)),
                ('requirements', django.contrib.postgres.fields.jsonb.JSONField(default=dict)),
                ('scheduling_class', models.CharField(choices=[('IN', 'Interactive'), ('BA', 'Batch')], default='BA', max_length=2)),
                ('contributor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'permissions': (('view_process', 'Can view process'), ('share_process', 'Can share process'), ('owner_process', 'Is owner of the process')),
                'get_latest_by': 'version',
                'abstract': False,
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='Relation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', resolwe.flow.models.fields.ResolweSlugField(max_length=100, populate_from='name', unique_with=('version',))),
                ('version', versionfield.VersionField(default='0.0.0')),
                ('name', models.CharField(max_length=100)),
                ('created', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('modified', models.DateTimeField(auto_now=True, db_index=True)),
                ('label', models.CharField(blank=True, max_length=100, null=True)),
                ('collection', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='flow.Collection')),
                ('contributor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('entities', models.ManyToManyField(through='flow.PositionInRelation', to='flow.Entity')),
            ],
            options={
                'permissions': (('view_relation', 'Can view relation'), ('edit_relation', 'Can edit relation'), ('share_relation', 'Can share relation'), ('owner_relation', 'Is owner of the relation')),
                'get_latest_by': 'version',
                'abstract': False,
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='RelationType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('ordered', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Storage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', resolwe.flow.models.fields.ResolweSlugField(max_length=100, populate_from='name', unique_with=('version',))),
                ('version', versionfield.VersionField(default='0.0.0')),
                ('name', models.CharField(max_length=100)),
                ('created', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('modified', models.DateTimeField(auto_now=True, db_index=True)),
                ('json', django.contrib.postgres.fields.jsonb.JSONField()),
                ('contributor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('data', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='flow.Data')),
            ],
            options={
                'get_latest_by': 'version',
                'abstract': False,
                'default_permissions': (),
            },
        ),
        migrations.AddField(
            model_name='relation',
            name='type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='flow.RelationType'),
        ),
        migrations.AddField(
            model_name='positioninrelation',
            name='relation',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='flow.Relation'),
        ),
        migrations.AddField(
            model_name='data',
            name='descriptor_schema',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='flow.DescriptorSchema'),
        ),
        migrations.AddField(
            model_name='data',
            name='parents',
            field=models.ManyToManyField(related_name='children', to='flow.Data'),
        ),
        migrations.AddField(
            model_name='data',
            name='process',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='flow.Process'),
        ),
        migrations.AddField(
            model_name='collection',
            name='data',
            field=models.ManyToManyField(to='flow.Data'),
        ),
        migrations.AddField(
            model_name='collection',
            name='descriptor_schema',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='flow.DescriptorSchema'),
        ),
        migrations.AlterUniqueTogether(
            name='storage',
            unique_together=set([('slug', 'version')]),
        ),
        migrations.AlterUniqueTogether(
            name='relation',
            unique_together=set([('slug', 'version')]),
        ),
        migrations.AlterUniqueTogether(
            name='process',
            unique_together=set([('slug', 'version')]),
        ),
        migrations.AlterUniqueTogether(
            name='entity',
            unique_together=set([('slug', 'version')]),
        ),
        migrations.AlterUniqueTogether(
            name='descriptorschema',
            unique_together=set([('slug', 'version')]),
        ),
        migrations.AlterUniqueTogether(
            name='data',
            unique_together=set([('slug', 'version')]),
        ),
        migrations.AlterUniqueTogether(
            name='collection',
            unique_together=set([('slug', 'version')]),
        ),
    ]