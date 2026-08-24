from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Account, Allocation, AllocationType, Category, MoneyLocation, Owner, Transaction, TransactionType


class Phase4SearchAndSqlTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='phase4-user', password='test-password')
        self.client.force_login(self.user)
        self.owner = Owner.objects.create(name='Phase4 Owner')
        self.location = MoneyLocation.objects.create(name='Phase4 Bank', location_type='bank')
        self.account = Account.objects.create(name='Phase4 Wallet', money_location=self.location, currency='INR', total_balance=Decimal('1000'))
        self.allocation = Allocation.objects.create(account=self.account, type=AllocationType.SPENDABLE, balance=Decimal('1000'))
        self.category = Category.objects.create(name='Phase4 Food')
        Transaction.objects.create(account=self.account, owner=self.owner, money_location=self.location, allocation=self.allocation,
                                   category=self.category, type=TransactionType.EXPENSE, amount=Decimal('125'),
                                   metadata={'merchant': 'Phase4 Cafe', 'note': 'coffee'})

    def test_transaction_search_and_filters(self):
        response = self.client.get('/api/transactions/all/?search=Phase4%20Cafe&allocation=spendable')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['amount'], '125.00')

    def test_transaction_filter_options(self):
        response = self.client.get('/api/transactions/filter-options/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(x['id'] == str(self.account.id) for x in response.data['accounts']))
        self.assertTrue(any(x['id'] == str(self.category.id) for x in response.data['categories']))

    def test_transaction_search_requires_authentication(self):
        self.client.logout()
        response = self.client.get('/api/transactions/all/')
        self.assertEqual(response.status_code, 401)

    def test_saved_query_rejects_write_sql(self):
        self.client.post('/api/sql/saved/', {'name': 'unsafe', 'sql': 'DROP TABLE wallet_account;'}, format='json')
        response = self.client.post('/api/sql/saved/', {'name': 'unsafe', 'sql': 'DELETE FROM wallet_account'}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_saved_query_accepts_read_only_sql(self):
        response = self.client.post('/api/sql/saved/', {'name': 'accounts', 'sql': 'SELECT id, name FROM wallet_account'}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['sql'], 'SELECT id, name FROM wallet_account')

    def test_sql_history_and_schema_require_authentication(self):
        self.client.logout()
        self.assertEqual(self.client.get('/api/sql/history/').status_code, 401)
        self.assertEqual(self.client.get('/api/sql/schema/').status_code, 401)
