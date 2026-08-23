from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Account, Allocation, AllocationType


class WalletTests(TestCase):
    def setUp(self):
        self.acc = Account.objects.create(name='TestAccount')
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
        self.client.post(reverse('account-deposit', args=[self.acc.id]), {'amount': '500'}, content_type='application/json')
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

        resp2 = self.client.post(reverse('account-transfer-to-spendable', args=[self.acc.id]), {'amount': '200'}, content_type='application/json')
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        allocs2 = {a['type']: Decimal(a['balance']) for a in data2['allocations']}
        self.assertEqual(allocs2['spendable'], Decimal('800.00'))
        self.assertEqual(allocs2['savings'], Decimal('200.00'))

    def test_summary_and_export(self):
        self.client.post(reverse('account-deposit', args=[self.acc.id]), {'amount': '1000'}, content_type='application/json')
        self.client.post(reverse('account-expense', args=[self.acc.id]), {'amount': '150', 'allocation': 'spendable', 'merchant': 'Groceries'}, content_type='application/json')

        summary_resp = self.client.get(reverse('account-summary', args=[self.acc.id]))
        self.assertEqual(summary_resp.status_code, 200)
        summary = summary_resp.json()
        self.assertEqual(summary['total_income'], '1000.00')
        self.assertEqual(summary['total_expenses'], '150.00')
        self.assertEqual(summary['net'], '850.00')

        export_resp = self.client.get(reverse('account-export-csv', args=[self.acc.id]))
        self.assertEqual(export_resp.status_code, 200)
        self.assertIn('expense', export_resp.content.decode('utf-8'))
        self.assertIn('deposit', export_resp.content.decode('utf-8'))

    def test_sql_playground_execute_and_schema(self):
        resp = self.client.post(
            reverse('sql-execute'),
            {'sql': "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name LIMIT 5;"},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload['status'], 'success')
        self.assertIn('rows', payload)
        self.assertGreaterEqual(payload['row_count'], 1)

        schema_resp = self.client.get(reverse('sql-schema'))
        self.assertEqual(schema_resp.status_code, 200)
        schema = schema_resp.json()
        self.assertIn('tables', schema)

        history_resp = self.client.get(reverse('sql-history'))
        self.assertEqual(history_resp.status_code, 200)
        self.assertTrue(len(history_resp.json()) >= 1)

        save_resp = self.client.post(
            reverse('sql-saved-queries'),
            {'name': 'Sample Query', 'sql': 'SELECT 1 AS answer;'},
            content_type='application/json',
        )
        self.assertEqual(save_resp.status_code, 201)
        self.assertEqual(save_resp.json()['name'], 'Sample Query')

        blocked_resp = self.client.post(
            reverse('sql-execute'),
            {'sql': "DROP TABLE wallet_account;"},
            content_type='application/json',
        )
        self.assertEqual(blocked_resp.status_code, 400)
