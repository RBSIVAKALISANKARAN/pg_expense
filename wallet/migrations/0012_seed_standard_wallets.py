from decimal import Decimal

from django.db import migrations


def seed_standard_wallets(apps, schema_editor):
    Account = apps.get_model('wallet', 'Account')
    Allocation = apps.get_model('wallet', 'Allocation')
    MoneyLocation = apps.get_model('wallet', 'MoneyLocation')
    MoneyPool = apps.get_model('wallet', 'MoneyPool')
    Owner = apps.get_model('wallet', 'Owner')

    owner, _ = Owner.objects.get_or_create(name='Me', defaults={'active': True})

    # Rename the old TMB location/account to the application's primary wallet name.
    rbs_location = MoneyLocation.objects.filter(name='rbsankaran_acc').first()
    tmb_location = MoneyLocation.objects.filter(name='TMB Bank').first()
    if not rbs_location and tmb_location:
        tmb_location.name = 'rbsankaran_acc'
        tmb_location.location_type = 'bank'
        tmb_location.save(update_fields=['name', 'location_type'])
        rbs_location = tmb_location
    elif not rbs_location:
        rbs_location = MoneyLocation.objects.create(
            name='rbsankaran_acc', location_type='bank', active=True,
        )

    Account.objects.filter(name='TMB_GPAY').update(name='rbsankaran_acc')

    standard_locations = [
        ('rbsankaran_acc', 'bank'),
        ('Amma Cash', 'cash'),
        ('Appa Cash', 'cash'),
        ('Change Cash', 'change_cash'),
        ('Travel Card', 'travel_card'),
    ]

    for location_name, location_type in standard_locations:
        location, _ = MoneyLocation.objects.get_or_create(
            name=location_name,
            defaults={'location_type': location_type, 'active': True},
        )
        location.location_type = location_type
        location.active = True
        location.save(update_fields=['location_type', 'active'])

        account = Account.objects.filter(money_location=location).first()
        if not account:
            account = Account.objects.create(
                name=location_name,
                money_location=location,
                currency='INR',
                total_balance=Decimal('0'),
            )
        elif location_name == 'rbsankaran_acc' and account.name == 'TMB_GPAY':
            account.name = 'rbsankaran_acc'
            account.save(update_fields=['name'])

        for allocation_type in ('spendable', 'savings'):
            allocation, _ = Allocation.objects.get_or_create(
                account=account,
                type=allocation_type,
                defaults={'balance': Decimal('0')},
            )
            MoneyPool.objects.get_or_create(
                account=account,
                owner=owner,
                location=location,
                allocation_type=allocation_type,
                defaults={'current_amount': allocation.balance},
            )


def reverse_seed_standard_wallets(apps, schema_editor):
    # This migration intentionally keeps created wallet data on rollback.
    # Renaming a real user's financial wallet back automatically could be destructive.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('wallet', '0011_fix_moneypool_location_uniqueness'),
    ]

    operations = [
        migrations.RunPython(seed_standard_wallets, reverse_seed_standard_wallets),
    ]
