# Generated by Django 3.2.12 on 2022-02-21 07:08

from django.db import connection, migrations, models


def migrate_storage_table(apps, schema_editor):
    with connection.cursor() as c:
        table_name = "flow_storage"
        new_id = "new_id"
        unique_index_name = f"{table_name}_new_id_pkey"
        storage_data_fk_name = (
            "flow_storage_data_storage_id_a5b557e5_fk_flow_storage_id"
        )
        # Create new column.
        query = f"""BEGIN TRANSACTION;
        
-- explicitly lock the table against other changes (safety)
LOCK TABLE {table_name} IN EXCLUSIVE MODE;

-- add new_id column
ALTER TABLE {table_name} ADD COLUMN {new_id} BIGINT;

-- copy values from id column to new_id column
UPDATE {table_name} SET {new_id} = id;

CREATE UNIQUE INDEX IF NOT EXISTS {unique_index_name} ON {table_name}({new_id});

-- remove fk constraint from flow_storage_data table
ALTER table flow_storage_data DROP CONSTRAINT IF EXISTS {storage_data_fk_name};

-- drop and create the PK using existing index
ALTER TABLE {table_name} DROP CONSTRAINT {table_name}_pkey, ADD CONSTRAINT {table_name}_pkey PRIMARY KEY USING INDEX {unique_index_name};

-- transfer the sequence
ALTER SEQUENCE {table_name}_id_seq OWNED BY {table_name}.{new_id};
ALTER TABLE {table_name} ALTER COLUMN {new_id} SET DEFAULT nextval('{table_name}_id_seq');

-- drop and rename the columns
ALTER TABLE {table_name} DROP COLUMN id;
ALTER TABLE {table_name} RENAME COLUMN {new_id} TO id;

-- add deleted foreign key constraint on table flow_storage_data
ALTER TABLE flow_storage_data ADD CONSTRAINT {storage_data_fk_name} FOREIGN KEY (storage_id) REFERENCES flow_storage(id) DEFERRABLE INITIALLY DEFERRED;

COMMIT;"""
        c.execute(query)


class Migration(migrations.Migration):

    dependencies = [("flow", "0004_data_process_resources")]

    operations = [
        migrations.AlterField(
            model_name="collection",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.AlterField(
            model_name="data",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.AlterField(
            model_name="datadependency",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.AlterField(
            model_name="datamigrationhistory",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.AlterField(
            model_name="descriptorschema",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.AlterField(
            model_name="entity",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.AlterField(
            model_name="process",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.AlterField(
            model_name="processmigrationhistory",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.AlterField(
            model_name="relation",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.AlterField(
            model_name="relationpartition",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.AlterField(
            model_name="relationtype",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.AlterField(
            model_name="worker",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.RunPython(migrate_storage_table),
        # Make a noop migration so that Django will detect id is now bigint.
        migrations.AlterField(
            model_name="storage",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
    ]
