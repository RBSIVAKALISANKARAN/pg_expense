from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Account, Allocation, AllocationType, Category, FoodProfile, Item, MoneyLocation, Owner, SubCategory, Transaction


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

    def test_default_owner_and_location_are_recorded_on_transaction(self):
        owner = Owner.objects.create(name='Me')
        location = MoneyLocation.objects.create(name='TMB Bank')
        self.client.post(
            reverse('account-deposit', args=[self.acc.id]),
            {'amount': '1000', 'owner': owner.id, 'money_location': location.id, 'note': 'salary'},
            content_type='application/json',
        )
        tx = Transaction.objects.filter(account=self.acc).latest('created_at')
        self.assertEqual(tx.owner_id, owner.id)
        self.assertEqual(tx.money_location_id, location.id)
        self.assertIsNotNone(tx.source_pool)

    def test_money_pools_track_allocation_totals(self):
        owner = Owner.objects.create(name='Me')
        location = MoneyLocation.objects.create(name='TMB Bank')

        self.client.post(
            reverse('account-deposit', args=[self.acc.id]),
            {'amount': '1000', 'allocate_to_savings': '300', 'owner': owner.id, 'money_location': location.id},
            content_type='application/json',
        )

        spendable_pool = self.acc.allocations.get(type=AllocationType.SPENDABLE).money_pools.get(owner=owner, location=location)
        savings_pool = self.acc.allocations.get(type=AllocationType.SAVINGS).money_pools.get(owner=owner, location=location)
        self.assertEqual(spendable_pool.current_amount, Decimal('700.00'))
        self.assertEqual(savings_pool.current_amount, Decimal('300.00'))

        self.client.post(
            reverse('account-transfer-to-savings', args=[self.acc.id]),
            {'amount': '100'},
            content_type='application/json',
        )

        spendable_pool.refresh_from_db()
        savings_pool.refresh_from_db()
        self.assertEqual(spendable_pool.current_amount, Decimal('600.00'))
        self.assertEqual(savings_pool.current_amount, Decimal('400.00'))

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

    def test_category_subcategory_item_food_profile_and_settings_api(self):
        category_resp = self.client.post(reverse('categories-list-create'), {'name': 'Food', 'description': 'Meals'}, content_type='application/json')
        self.assertEqual(category_resp.status_code, 201)
        category_id = category_resp.json()['id']

        subcategory_resp = self.client.post(
            reverse('subcategories-list-create'),
            {'category': category_id, 'name': 'Lunch', 'description': 'Midday meals'},
            content_type='application/json',
        )
        self.assertEqual(subcategory_resp.status_code, 201)
        self.assertEqual(subcategory_resp.json()['name'], 'Lunch')

        item_resp = self.client.post(
            reverse('items-list-create'),
            {'category': category_id, 'subcategory': subcategory_resp.json()['id'], 'name': 'Meals', 'description': 'Food item', 'is_custom': True, 'food_group': 'snack', 'health_classification': 'junk', 'sugary': 'yes'},
            content_type='application/json',
        )
        self.assertEqual(item_resp.status_code, 201)
        self.assertEqual(item_resp.json()['name'], 'Meals')
        self.assertEqual(item_resp.json()['subcategory_name'], 'Lunch')

        profile_resp = self.client.get(reverse('food-profiles'))
        self.assertEqual(profile_resp.status_code, 200)
        self.assertTrue(any(item['item_name'] == 'Meals' for item in profile_resp.json()))

        self.client.post(reverse('account-deposit', args=[self.acc.id]), {'amount': '1000'}, content_type='application/json')
        expense_resp = self.client.post(
            reverse('account-expense', args=[self.acc.id]),
            {'amount': '50', 'allocation': 'spendable', 'merchant': 'Cafe', 'meal': 'breakfast'},
            content_type='application/json',
        )
        self.assertEqual(expense_resp.status_code, 200)
        tx = Transaction.objects.filter(account=self.acc).latest('created_at')
        self.assertEqual(tx.meal, 'breakfast')

        settings_resp = self.client.get(reverse('app-settings'))
        self.assertEqual(settings_resp.status_code, 200)
        self.assertEqual(settings_resp.json()['currency_default'], 'INR')

    def test_family_money_list_endpoints(self):
        Owner.objects.create(name='Me')
        Owner.objects.create(name='Appa')
        MoneyLocation.objects.create(name='TMB Bank')
        MoneyLocation.objects.create(name='Appa Cash')

        owners_resp = self.client.get(reverse('owners-list'))
        self.assertEqual(owners_resp.status_code, 200)
        self.assertTrue(any(item['name'] == 'Me' for item in owners_resp.json()))
        self.assertTrue(any(item['name'] == 'Appa' for item in owners_resp.json()))

        locations_resp = self.client.get(reverse('money-locations-list'))
        self.assertEqual(locations_resp.status_code, 200)
        self.assertTrue(any(item['name'] == 'TMB Bank' for item in locations_resp.json()))
        self.assertTrue(any(item['name'] == 'Appa Cash' for item in locations_resp.json()))
        self.assertTrue(any(item['name'] == 'Amma Cash' for item in locations_resp.json()))

        pools_resp = self.client.get(reverse('money-pools-list'))
        self.assertEqual(pools_resp.status_code, 200)
