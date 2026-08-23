from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Account, Allocation, AllocationType, MoneyLocation, MoneyPool, Owner


class ExpenseFlowReconciliationTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create(name='ReconciliationTest')
        Allocation.objects.get_or_create(account=self.account, type=AllocationType.SPENDABLE)
        Allocation.objects.get_or_create(account=self.account, type=AllocationType.SAVINGS)

    def post(self, name, payload):
        return self.client.post(
            reverse(name, args=[self.account.id]),
            payload,
            content_type='application/json',
        )

    def test_expense_rejects_location_different_from_account_location_without_mutating_balance(self):
        owner = Owner.objects.create(name='Me')
        bank = MoneyLocation.objects.create(name='TMB Bank')
        cash = MoneyLocation.objects.create(name='Appa Cash')

        deposit = self.post('account-deposit', {
            'amount': '500',
            'owner': owner.id,
            'money_location': bank.id,
        })
        self.assertEqual(deposit.status_code, 200, deposit.content)

        self.account.refresh_from_db()
        before_balance = self.account.total_balance
        before_pool_total = MoneyPool.objects.filter(account=self.account).aggregate_total if False else sum(
            MoneyPool.objects.filter(account=self.account).values_list('current_amount', flat=True)
        )

        response = self.post('account-expense', {
            'amount': '50',
            'allocation': 'spendable',
            'owner': owner.id,
            'money_location': cash.id,
        })

        self.assertEqual(response.status_code, 400, response.content)
        self.account.refresh_from_db()
        self.assertEqual(self.account.total_balance, before_balance)
        after_pool_total = sum(
            MoneyPool.objects.filter(account=self.account).values_list('current_amount', flat=True)
        )
        self.assertEqual(after_pool_total, before_pool_total)
        self.assertFalse(MoneyPool.objects.filter(account=self.account, location=cash).exists())

    def test_expense_keeps_account_allocations_and_pools_reconciled(self):
        owner = Owner.objects.create(name='Me')
        bank = MoneyLocation.objects.create(name='TMB Bank')

        self.assertEqual(self.post('account-deposit', {
            'amount': '1000',
            'owner': owner.id,
            'money_location': bank.id,
            'allocate_to_savings': '300',
        }).status_code, 200)

        response = self.post('account-expense', {
            'amount': '125',
            'allocation': 'spendable',
            'owner': owner.id,
            'money_location': bank.id,
            'note': 'test expense',
        })
        self.assertEqual(response.status_code, 200, response.content)

        self.account.refresh_from_db()
        allocation_total = sum(self.account.allocations.values_list('balance', flat=True))
        pool_total = sum(MoneyPool.objects.filter(account=self.account).values_list('current_amount', flat=True))
        self.assertEqual(self.account.total_balance, Decimal('875.00'))
        self.assertEqual(allocation_total, self.account.total_balance)
        self.assertEqual(pool_total, self.account.total_balance)

    def test_transfer_endpoints_preserve_reconciliation(self):
        owner = Owner.objects.create(name='Me')
        bank = MoneyLocation.objects.create(name='TMB Bank')

        self.assertEqual(self.post('account-deposit', {
            'amount': '1000',
            'owner': owner.id,
            'money_location': bank.id,
        }).status_code, 200)

        to_savings = self.post('account-transfer-to-savings', {
            'amount': '250',
            'owner': owner.id,
            'money_location': bank.id,
        })
        self.assertEqual(to_savings.status_code, 200, to_savings.content)

        back = self.post('account-transfer-to-spendable', {
            'amount': '100',
            'owner': owner.id,
            'money_location': bank.id,
        })
        self.assertEqual(back.status_code, 200, back.content)

        self.account.refresh_from_db()
        allocation_total = sum(self.account.allocations.values_list('balance', flat=True))
        pool_total = sum(MoneyPool.objects.filter(account=self.account).values_list('current_amount', flat=True))
        self.assertEqual(self.account.total_balance, Decimal('1000.00'))
        self.assertEqual(allocation_total, self.account.total_balance)
        self.assertEqual(pool_total, self.account.total_balance)
