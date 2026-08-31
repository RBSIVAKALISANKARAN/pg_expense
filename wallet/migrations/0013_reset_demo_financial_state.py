from django.db import migrations


def reset_demo_financial_state(apps, schema_editor):
    if schema_editor.connection.alias != 'default':
        return

    Account = apps.get_model('wallet', 'Account')
    Allocation = apps.get_model('wallet', 'Allocation')
    MoneyPool = apps.get_model('wallet', 'MoneyPool')
    Transaction = apps.get_model('wallet', 'Transaction')

    # Start the demo branch with a clean financial ledger. Transaction-linked
    # food events are removed through their CASCADE relationship.
    Transaction.objects.all().delete()

    # Remove browser-test wallets that were accidentally left in the demo DB.
    Account.objects.filter(name__startswith='E2E ').delete()
    Account.objects.filter(name='Power Test Wallet').delete()

    Account.objects.all().update(total_balance=0)
    Allocation.objects.all().update(balance=0)
    MoneyPool.objects.all().update(current_amount=0)


def reverse_reset_demo_financial_state(apps, schema_editor):
    # Deleted transaction history cannot be reconstructed safely.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('wallet', '0012_mealoption'),
    ]

    operations = [
        migrations.RunPython(
            reset_demo_financial_state,
            reverse_code=reverse_reset_demo_financial_state,
        ),
    ]
