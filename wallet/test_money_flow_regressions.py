from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from .models import Account, Category, Transaction


class MoneyFlowRegressionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.food = Category.objects.create(name='Food')
        self.transport = Category.objects.create(name='Transport')
        self.client.post('/api/wallet/accounts/create/', {
            'name': 'UPI', 'location_type': 'bank', 'location_name': 'Regression UPI',
        }, format='json')
        self.upi = Account.objects.get(name='UPI')
        # 'Travel Card' is already seeded as a standard wallet by migrations, so
        # reuse it here instead of creating a second, colliding account with the
        # same name.
        self.travel = Account.objects.get(name='Travel Card')
        self.client.post(f'/api/accounts/{self.upi.id}/deposit/', {'amount': '1000'}, format='json')

    def test_missing_occurred_at_is_never_saved_as_null(self):
        response = self.client.post('/api/expense/entry/', {
            'account': str(self.upi.id), 'amount': '25', 'category': str(self.food.id),
        }, format='json')
        self.assertEqual(response.status_code, 201)
        tx = Transaction.objects.get(pk=response.data['id'])
        self.assertIsNotNone(tx.occurred_at)

    def test_partial_transport_edit_preserves_existing_transport_details(self):
        response = self.client.post('/api/expense/entry/', {
            'account': str(self.upi.id), 'amount': '50', 'category': str(self.food.id),
        }, format='json')
        self.assertEqual(response.status_code, 201)
        tx_id = response.data['id']

        response = self.client.patch(f'/api/transactions/{tx_id}/edit/', {
            'amount': '75', 'category': str(self.transport.id),
            'transport_from': 'Guindy', 'transport_to': 'T Nagar',
            'transport_mode': 'bus', 'bus_type': 'MTC', 'payment_method': 'upi',
        }, format='json')
        self.assertEqual(response.status_code, 200)

        response = self.client.patch(f'/api/transactions/{tx_id}/edit/', {'amount': '80'}, format='json')
        self.assertEqual(response.status_code, 200)
        tx = Transaction.objects.get(pk=tx_id)
        self.assertEqual(tx.amount, Decimal('80'))
        self.assertEqual(tx.metadata['transport_from'], 'Guindy')
        self.assertEqual(tx.metadata['transport_to'], 'T Nagar')
        self.assertEqual(tx.metadata['payment_method'], 'upi')

    def test_upi_to_travel_card_transfer_preserves_total_money(self):
        response = self.client.post('/api/wallet/transfer/', {
            'source_account': str(self.upi.id), 'destination_account': str(self.travel.id), 'amount': '300',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.upi.refresh_from_db()
        self.travel.refresh_from_db()
        self.assertEqual(self.upi.total_balance, Decimal('700'))
        self.assertEqual(self.travel.total_balance, Decimal('300'))
        self.assertEqual(self.upi.total_balance + self.travel.total_balance, Decimal('1000'))
