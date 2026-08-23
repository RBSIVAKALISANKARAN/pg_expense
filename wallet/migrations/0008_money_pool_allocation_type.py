# Generated manually to normalize MoneyPool allocation storage.

from django.db import migrations, models


def copy_allocation_type(apps, schema_editor):
    MoneyPool = apps.get_model('wallet', 'MoneyPool')
    for pool in MoneyPool.objects.select_related('allocation').all():
        pool.allocation_type = pool.allocation.type if pool.allocation_id else 'spendable'
        pool.save(update_fields=['allocation_type'])


class Migration(migrations.Migration):

    dependencies = [
        ('wallet', '0007_transaction_meal_foodprofile'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='moneypool',
            options={'ordering': ['owner__name', 'location__name', 'allocation_type']},
        ),
        migrations.AddField(
            model_name='moneypool',
            name='allocation_type',
            field=models.CharField(choices=[('spendable', 'Spendable'), ('savings', 'Savings')], max_length=20, null=True),
        ),
        migrations.RunPython(copy_allocation_type, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name='moneypool',
            name='unique_owner_location_allocation_pool',
        ),
        migrations.RemoveField(
            model_name='moneypool',
            name='allocation',
        ),
        migrations.AlterField(
            model_name='moneypool',
            name='allocation_type',
            field=models.CharField(choices=[('spendable', 'Spendable'), ('savings', 'Savings')], max_length=20),
        ),
        migrations.AddConstraint(
            model_name='moneypool',
            constraint=models.UniqueConstraint(fields=('owner', 'location', 'allocation_type'), name='unique_owner_location_allocation_type_pool'),
        ),
    ]
