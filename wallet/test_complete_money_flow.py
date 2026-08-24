from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Account, Category, MoneyLocationType, Transaction


class CompleteMoneyFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='complete-flow-user', password='test-password')
        self.client.force_login(self.user)
        self.food = Category.objects.create(name='Food')
        self.transport = Category.objects.create(name='Transport')

        response = self.client.post('/api/wallet/accounts/create/', {
            'name': 'UPI', 'currency': 'INR', 'location_type': 'bank', 'location_name': 'UPI Wallet',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.upi = Account.objects.get(name='UPI')

        self.travel = Account.objects.get(name='Travel Card')

        response = self.client.post(f'/api/accounts/{self.upi.id}/deposit/', {'amount': '1000', 'allocate_to_savings': '0'}, format='json')
        self.assertEqual(response.status_code, 200)

    def balance(self, account):
        account.refresh_from_db()
        return account.total_balance

    def test_transfer_moves_money_between_wallets_without_duplication(self):
        response = self.client.post('/api/wallet/transfer/', {
            'source_account': str(self.upi.id), 'destination_account': str(self.travel.id), 'amount': '300',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.balance(self.upi), Decimal('700'))
        self.assertEqual(self.balance(self.travel), Decimal('300'))
        self.assertEqual(self.balance(self.upi) + self.balance(self.travel), Decimal('1000'))

    def test_transport_expense_uses_actual_travel_card_wallet(self):
        response = self.client.post('/api/wallet/transfer/', {
            'source_account': str(self.upi.id), 'destination_account': str(self.travel.id), 'amount': '200',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        response = self.client.post('/api/expense/entry/', {
            'account': str(self.travel.id), 'amount': '80', 'allocation': 'spendable', 'category': str(self.transport.id),
            'transport_from': 'Home', 'transport_to': 'Office', 'transport_mode': 'bus',
            'bus_type': 'ordinary', 'payment_method': 'travel_card',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.balance(self.travel), Decimal('120'))
        self.assertEqual(self.balance(self.upi), Decimal('800'))

    def test_expense_revert_restores_balance(self):
        response = self.client.post('/api/expense/entry/', {
            'account': str(self.upi.id), 'amount': '100', 'allocation': 'spendable', 'category': str(self.food.id),
        }, format='json')
        self.assertEqual(response.status_code, 201)
        tx_id = response.data['id']
        self.assertEqual(self.balance(self.upi), Decimal('900'))
        response = self.client.delete(f'/api/transactions/{tx_id}/revert/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.balance(self.upi), Decimal('1000'))
        self.assertTrue(Transaction.objects.get(pk=tx_id).metadata['reverted'])

    def test_delete_is_a_soft_revert(self):
        response = self.client.post('/api/expense/entry/', {
            'account': str(self.upi.id), 'amount': '50', 'allocation': 'spendable', 'category': str(self.food.id),
        }, format='json')
        tx_id = response.data['id']
        response = self.client.delete(f'/api/transactions/{tx_id}/revert/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.balance(self.upi), Decimal('1000'))
        tx = Transaction.objects.get(pk=tx_id)
        self.assertTrue(tx.metadata['deleted'])
        self.assertTrue(tx.metadata['reverted'])

    def test_live_schema_and_reports_are_available(self):
        response = self.client.get('/api/sql/schema-live-exact/')
        self.assertEqual(response.status_code, 200)
        table_names = {table['name'] for table in response.data['tables']}
        self.assertIn('wallet_transaction', table_names)
        response = self.client.get('/api/reports/data/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('category', response.data)
