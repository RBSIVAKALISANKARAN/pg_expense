from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from .feature_models import MealOption
from .models import Account, AllocationType, MoneyLocation, Owner, Transaction, TransactionType


class ExpenseWalletFeatureTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = Owner.objects.create(name='Me')
        self.location = MoneyLocation.objects.create(name='UPI Wallet', location_type='bank')
        self.travel = MoneyLocation.objects.create(name='Travel Card', location_type='travel_card')
        self.account = Account.objects.create(name='UPI', currency='INR', money_location=self.location)
        self.account.allocations.create(type=AllocationType.SPENDABLE, balance=Decimal('1000'))
        self.account.allocations.create(type=AllocationType.SAVINGS, balance=Decimal('0'))
        self.account.total_balance = Decimal('1000')
        self.account.save(update_fields=['total_balance'])
        self.client.post(f'/api/accounts/{self.account.id}/deposit/', {'amount': '100', 'owner': str(self.owner.id), 'money_location': str(self.location.id)})

    def test_meal_master_is_persistent(self):
        response = self.client.post('/api/meals/', {'name': 'Tea Time'})
        self.assertEqual(response.status_code, 201)
        self.assertTrue(MealOption.objects.filter(name='Tea Time').exists())

    def test_expense_revert_restores_balance(self):
        response = self.client.post('/api/expense/entry/', {
            'account': str(self.account.id), 'amount': '50', 'allocation': 'spendable',
            'owner': str(self.owner.id), 'money_location': str(self.location.id),
            'occurred_at': '2026-08-24T10:00:00+05:30',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        tx_id = response.data['id']
        self.account.refresh_from_db()
        before = self.account.total_balance
        self.assertEqual(before, Decimal('1050'))
        response = self.client.post(f'/api/transactions/{tx_id}/revert/')
        self.assertEqual(response.status_code, 200)
        self.account.refresh_from_db()
        self.assertEqual(self.account.total_balance, Decimal('1100'))
        self.assertTrue(Transaction.objects.get(pk=tx_id).metadata['reverted'])

    def test_transport_metadata_is_saved(self):
        response = self.client.post('/api/expense/entry/', {
            'account': str(self.account.id), 'amount': '25', 'allocation': 'spendable',
            'owner': str(self.owner.id), 'money_location': str(self.location.id),
            'transport_from': 'Central', 'transport_to': 'Guindy', 'transport_mode': 'bus',
            'bus_type': 'MTC', 'payment_method': 'travel_card',
            'occurred_at': '2026-08-24T10:00:00+05:30',
        }, format='json')
        # Uncategorized is not the Transport category, so this verifies the
        # fields remain optional until Transport is actually selected.
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['type'], TransactionType.EXPENSE)

    def test_sql_playground_is_read_only(self):
        response = self.client.post('/api/sql/execute-live/', {'sql': 'SELECT 1'}, format='json')
        self.assertEqual(response.status_code, 200)
        response = self.client.post('/api/sql/execute-live/', {'sql': 'DELETE FROM wallet_transaction'}, format='json')
        self.assertEqual(response.status_code, 400)
