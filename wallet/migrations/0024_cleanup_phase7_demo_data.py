from django.db import migrations


def cleanup_phase7_demo_data(apps, schema_editor):
    if schema_editor.connection.alias != 'default':
        return

    Account = apps.get_model('wallet', 'Account')
    MoneyLocation = apps.get_model('wallet', 'MoneyLocation')
    Owner = apps.get_model('wallet', 'Owner')
    Category = apps.get_model('wallet', 'Category')
    SubCategory = apps.get_model('wallet', 'SubCategory')
    Item = apps.get_model('wallet', 'Item')
    MealOption = apps.get_model('wallet', 'MealOption')
    Transaction = apps.get_model('wallet', 'Transaction')
    FoodEvent = apps.get_model('wallet', 'FoodEvent')
    FoodEventItem = apps.get_model('wallet', 'FoodEventItem')

    # Phase 7 browser fixtures used E2E-prefixed master-data and wallet names.
    # Remove those leftovers without touching the canonical application data.
    Transaction.objects.all().delete()
    FoodEventItem.objects.all().delete()
    FoodEvent.objects.all().delete()
    Account.objects.filter(name__startswith='E2E ').delete()
    Account.objects.filter(name='Power Test Wallet').delete()
    MoneyLocation.objects.filter(name__startswith='E2E ').delete()
    Owner.objects.filter(name__startswith='E2E ').delete()
    Item.objects.filter(name__startswith='E2E ').delete()
    SubCategory.objects.filter(name__startswith='E2E ').delete()
    Category.objects.filter(name__startswith='E2E ').delete()
    MealOption.objects.filter(name__startswith='E2E ').delete()

    # The demo workspace starts with every surviving wallet at zero while
    # retaining the standard wallet records supplied by post_migrate signals.
    Account.objects.all().update(total_balance=0)
    Allocation = apps.get_model('wallet', 'Allocation')
    MoneyPool = apps.get_model('wallet', 'MoneyPool')
    Allocation.objects.all().update(balance=0)
    MoneyPool.objects.all().update(current_amount=0)


class Migration(migrations.Migration):
    dependencies = [
        ('wallet', '0023_reset_demo_financial_state'),
    ]

    operations = [
        migrations.RunPython(cleanup_phase7_demo_data),
    ]
