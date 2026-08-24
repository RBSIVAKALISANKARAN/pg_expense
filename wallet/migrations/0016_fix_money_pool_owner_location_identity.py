from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wallet', '0015_merge_20260824_1030'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                WITH ranked AS (
                    SELECT id,
                           ROW_NUMBER() OVER (
                               PARTITION BY owner_id, location_id, allocation_type
                               ORDER BY created_at ASC, id ASC
                           ) AS row_num
                    FROM wallet_moneypool
                )
                DELETE FROM wallet_moneypool
                WHERE id IN (SELECT id FROM ranked WHERE row_num > 1);
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RemoveConstraint(
            model_name='moneypool',
            name='unique_account_owner_location_allocation_pool',
        ),
        migrations.AddConstraint(
            model_name='moneypool',
            constraint=models.UniqueConstraint(
                fields=('owner', 'location', 'allocation_type'),
                name='unique_owner_location_allocation_pool',
            ),
        ),
    ]
