from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('wallet', '0016_fix_money_pool_owner_location_identity'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                WITH ranked AS (
                    SELECT id,
                           ROW_NUMBER() OVER (
                               PARTITION BY name
                               ORDER BY created_at ASC, id ASC
                           ) AS row_num
                    FROM wallet_account
                )
                DELETE FROM wallet_account
                WHERE id IN (SELECT id FROM ranked WHERE row_num > 1);
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
