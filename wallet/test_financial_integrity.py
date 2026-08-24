from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import (
    Account,
    Allocation,
    AllocationType,
    Category,
    MoneyLocation,
    MoneyPool,
    Owner,
    Transaction,
    TransactionType,
)


class FinancialIntegrityTests(TestCase):
    def setUp(self):
        self.owner = Owner.objects.get(name='Me')
        self.location = MoneyLocation.objects.get(name='rbsankaran_acc')
        self.source = Account.objects.get(name='rbsankaran_acc')
        self.destination = Account.objects.get(name='Travel Card')

    def deposit(self, account, amount, savings='0'):
        return self.client.post(
            reverse('account-deposit', args=[account.id]),
            {
                'amount': str(amount),
                'allocate_to_savings': str(savings),
                'owner': str(self.owner.id),
                'money_location': str(account.money_location_id),
            },
            content_type='application/json',
        )

    def test_same_owner_and_location_keep_money_pools_separate_per_account(self):
        second = Account.objects.create(
            name='Same Location Second Account',
            money_location=self.location,
            currency='INR',
        )
        Allocation.objects.create(account=second, type=AllocationType.SPENDABLE)
        Allocation.objects.create(account=second, type=AllocationType.SAVINGS)

        first_deposit = self.deposit(self.source, '1000')
        second_deposit = self.deposit(second, '500')

        self.assertEqual(first_deposit.status_code, 200, first_deposit.content)
        self.assertEqual(second_deposit.status_code, 200, second_deposit.content)

        source_pool = MoneyPool.objects.get(
            account=self.source, owner=self.owner, location=self.location,
            allocation_type=AllocationType.SPENDABLE,
        )
        second_pool = MoneyPool.objects.get(
            account=second, owner=self.owner, location=self.location,
            allocation_type=AllocationType.SPENDABLE,
        )
        self.assertNotEqual(source_pool.pk, second_pool.pk)
        self.assertEqual(source_pool.current_amount, Decimal('1000.00'))
        self.assertEqual(second_pool.current_amount, Decimal('500.00'))

        self.source.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(self.source.total_balance, Decimal('1000.00'))
        self.assertEqual(second.total_balance, Decimal('500.00'))

    def test_savings_and_spendable_transfers_preserve_total_balance_and_reconcile(self):
        response = self.deposit(self.source, '1000', '300')
        self.assertEqual(response.status_code, 200, response.content)

        response = self.client.post(
            reverse('account-transfer-to-savings', args=[self.source.id]),
            {'amount': '100'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200, response.content)

        response = self.client.post(
            reverse('account-transfer-to-spendable', args=[self.source.id]),
            {'amount': '50'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200, response.content)

        spendable = Allocation.objects.get(account=self.source, type=AllocationType.SPENDABLE)
        savings = Allocation.objects.get(account=self.source, type=AllocationType.SAVINGS)
        self.source.refresh_from_db()
        self.assertEqual(spendable.balance, Decimal('650.00'))
        self.assertEqual(savings.balance, Decimal('350.00'))
        self.assertEqual(self.source.total_balance, Decimal('1000.00'))

        pools = MoneyPool.objects.filter(account=self.source, owner=self.owner, location=self.location)
        self.assertEqual(pools.get(allocation_type=AllocationType.SPENDABLE).current_amount, Decimal('650.00'))
        self.assertEqual(pools.get(allocation_type=AllocationType.SAVINGS).current_amount, Decimal('350.00'))

    def test_expense_and_revert_restore_every_financial_balance(self):
        self.assertEqual(self.deposit(self.source, '1000').status_code, 200)
        category = Category.objects.create(name='Financial Integrity Test Category')

        expense = self.client.post(
            reverse('account-expense', args=[self.source.id]),
            {
                'amount': '250',
                'allocation': AllocationType.SPENDABLE,
                'category': str(category.id),
            },
            content_type='application/json',
        )
        self.assertEqual(expense.status_code, 200, expense.content)
        tx = Transaction.objects.get(account=self.source, type=TransactionType.EXPENSE, amount=Decimal('250.00'))

        self.source.refresh_from_db()
        self.assertEqual(self.source.total_balance, Decimal('750.00'))
        self.assertEqual(Allocation.objects.get(account=self.source, type=AllocationType.SPENDABLE).balance, Decimal('750.00'))

        reverted = self.client.post(
            reverse('wallet-transaction-revert', args=[tx.id]),
            content_type='application/json',
        )
        self.assertEqual(reverted.status_code, 200, reverted.content)

        self.source.refresh_from_db()
        self.assertEqual(self.source.total_balance, Decimal('1000.00'))
        self.assertEqual(Allocation.objects.get(account=self.source, type=AllocationType.SPENDABLE).balance, Decimal('1000.00'))
        pool = MoneyPool.objects.get(account=self.source, owner=self.owner, location=self.location, allocation_type=AllocationType.SPENDABLE)
        self.assertEqual(pool.current_amount, Decimal('1000.00'))
        tx.refresh_from_db()
        self.assertTrue(tx.metadata.get('reverted'))

    def test_expense_cannot_overdraw_specific_account_pool(self):
        self.assertEqual(self.deposit(self.source, '500').status_code, 200)
        second = Account.objects.create(name='Pool Isolation Account', money_location=self.location, currency='INR')
        Allocation.objects.create(account=second, type=AllocationType.SPENDABLE)
        Allocation.objects.create(account=second, type=AllocationType.SAVINGS)
        self.assertEqual(self.deposit(second, '100').status_code, 200)

        response = self.client.post(
            reverse('account-expense', args=[second.id]),
            {'amount': '150', 'allocation': AllocationType.SPENDABLE},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        second.refresh_from_db()
        self.assertEqual(second.total_balance, Decimal('100.00'))
        self.assertEqual(Transaction.objects.filter(account=second, type=TransactionType.EXPENSE).count(), 0)
