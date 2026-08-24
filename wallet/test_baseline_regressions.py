from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Account, Allocation, AllocationType, Category, MoneyLocation, MoneyPool, Owner, Transaction


class BaselineRegressionTests(TestCase):
    """Restore the four baseline behaviors lost during the Phase 2 test-file refactor."""

    def setUp(self):
        self.user = User.objects.create_user(username='baseline-regression', password='test-password')
        self.client.force_login(self.user)
        self.account = Account.objects.create(name='Baseline Regression Account')
        Allocation.objects.get_or_create(account=self.account, type=AllocationType.SPENDABLE)
        Allocation.objects.get_or_create(account=self.account, type=AllocationType.SAVINGS)

    def deposit(self, amount='1000'):
        return self.client.post(
            reverse('account-deposit', args=[self.account.id]),
            {'amount': amount},
            content_type='application/json',
        )

    def test_summary_and_csv_export_remain_consistent(self):
        self.assertEqual(self.deposit('1000').status_code, 200)
        expense = self.client.post(
            reverse('account-expense', args=[self.account.id]),
            {'amount': '150', 'allocation': AllocationType.SPENDABLE, 'merchant': 'Groceries'},
            content_type='application/json',
        )
        self.assertEqual(expense.status_code, 200, expense.content)

        summary = self.client.get(reverse('account-summary', args=[self.account.id]))
        self.assertEqual(summary.status_code, 200)
        payload = summary.json()
        self.assertEqual(payload['total_income'], '1000.00')
        self.assertEqual(payload['total_expenses'], '150.00')
        self.assertEqual(payload['net'], '850.00')

        export = self.client.get(reverse('account-export-csv', args=[self.account.id]))
        self.assertEqual(export.status_code, 200)
        csv = export.content.decode('utf-8')
        self.assertIn('expense', csv)
        self.assertIn('deposit', csv)

    def test_sql_playground_read_schema_history_and_block_write(self):
        response = self.client.post(
            reverse('sql-execute'),
            {'sql': "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name LIMIT 5;"},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload['status'], 'success')
        self.assertIn('rows', payload)

        schema = self.client.get(reverse('sql-schema'))
        self.assertEqual(schema.status_code, 200)
        self.assertIn('tables', schema.json())

        history = self.client.get(reverse('sql-history'))
        self.assertEqual(history.status_code, 200)
        self.assertGreaterEqual(len(history.json()), 1)

        blocked = self.client.post(
            reverse('sql-execute'),
            {'sql': 'DROP TABLE wallet_account;'},
            content_type='application/json',
        )
        self.assertEqual(blocked.status_code, 400)

    def test_category_item_food_profile_and_settings_api_work_together(self):
        category = Category.objects.create(name='Baseline Food', description='Regression category')
        subcategory = self.client.post(
            reverse('subcategories-list-create'),
            {'category': category.id, 'name': 'Baseline Lunch'},
            content_type='application/json',
        )
        self.assertEqual(subcategory.status_code, 201, subcategory.content)

        item = self.client.post(
            reverse('items-list-create'),
            {
                'category': category.id,
                'subcategory': subcategory.json()['id'],
                'name': 'Baseline Meal',
                'is_custom': True,
                'food_group': 'snack',
                'health_classification': 'junk',
                'sugary': 'yes',
            },
            content_type='application/json',
        )
        self.assertEqual(item.status_code, 201, item.content)
