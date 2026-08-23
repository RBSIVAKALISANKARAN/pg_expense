from decimal import Decimal

from django.test import TestCase

from .models import Account, AllocationType, MoneyLocation, MoneyPool, Owner


class MoneyPoolIntegrityTests(TestCase):
    def test_same_account_owner_and_allocation_can_have_different_locations(self):
        account = Account.objects.create(name='PoolTest')
        owner = Owner.objects.create(name='PoolOwner')
        bank = MoneyLocation.objects.create(name='Test Bank')
        cash = MoneyLocation.objects.create(name='Test Cash', location_type='cash')

        bank_pool = MoneyPool.objects.create(
            account=account,
            owner=owner,
            location=bank,
            allocation_type=AllocationType.SPENDABLE,
            current_amount=Decimal('100.00'),
        )
        cash_pool = MoneyPool.objects.create(
            account=account,
            owner=owner,
            location=cash,
            allocation_type=AllocationType.SPENDABLE,
            current_amount=Decimal('50.00'),
        )

        self.assertNotEqual(bank_pool.pk, cash_pool.pk)
        self.assertEqual(
            MoneyPool.objects.filter(
                account=account,
                owner=owner,
                allocation_type=AllocationType.SPENDABLE,
            ).count(),
            2,
        )
