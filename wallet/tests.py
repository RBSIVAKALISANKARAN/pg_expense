from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Account, Allocation, AllocationType


class WalletTests(TestCase):
    def setUp(self):
        self.acc = Account.objects.create(name='TestAccount')
        # ensure allocations are present
        Allocation.objects.get_or_create(account=self.acc, type=AllocationType.SPENDABLE)
        Allocation.objects.get_or_create(account=self.acc, type=AllocationType.SAVINGS)

    def test_deposit_with_savings_allocation(self):
        url = reverse('account-deposit', args=[self.acc.id])
        resp = self.client.post(url, {'amount': '1000', 'allocate_to_savings': '300', 'note': 'initial'}, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['total_balance'], '1000.00')
        allocs = {a['type']: Decimal(a['balance']) for a in data['allocations']}
        self.assertEqual(allocs['spendable'], Decimal('700.00'))
        self.assertEqual(allocs['savings'], Decimal('300.00'))

    def test_expense_from_spendable(self):
        # deposit first
        self.client.post(reverse('account-deposit', args=[self.acc.id]), {'amount': '500'}, content_type='application/json')
        # expense
        resp = self.client.post(reverse('account-expense', args=[self.acc.id]), {'amount': '200', 'allocation': 'spendable', 'merchant': 'Cafe'}, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['total_balance'], '300.00')

    def test_transfer_to_savings_and_back(self):
        self.client.post(reverse('account-deposit', args=[self.acc.id]), {'amount': '1000'}, content_type='application/json')
        resp = self.client.post(reverse('account-transfer-to-savings', args=[self.acc.id]), {'amount': '400'}, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        allocs = {a['type']: Decimal(a['balance']) for a in data['allocations']}
        self.assertEqual(allocs['spendable'], Decimal('600.00'))
        self.assertEqual(allocs['savings'], Decimal('400.00'))
        # transfer back
        resp2 = self.client.post(reverse('account-transfer-to-spendable', args=[self.acc.id]), {'amount': '200'}, content_type='application/json')
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        allocs2 = {a['type']: Decimal(a['balance']) for a in data2['allocations']}
        self.assertEqual(allocs2['spendable'], Decimal('800.00'))
        self.assertEqual(allocs2['savings'], Decimal('200.00'))
