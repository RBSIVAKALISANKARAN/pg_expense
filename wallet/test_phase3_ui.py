from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Account


class Phase3SavingsUiContractTests(TestCase):
    def setUp(self):
        get_user_model().objects.create_user(username='phase3-savings', password='phase3-pass')
        self.client = APIClient()
        self.client.login(username='phase3-savings', password='phase3-pass')
        self.account = Account.objects.create(name='Phase 3 Wallet', currency='INR')

    def test_savings_and_spendable_controls_preserve_total(self):
        deposit = self.client.post(f'/api/accounts/{self.account.id}/deposit/', {
            'amount': '600.00',
            'allocate_to_savings': '100.00',
        }, format='json')
        self.assertEqual(deposit.status_code, 200)
        response = self.client.post(f'/api/accounts/{self.account.id}/transfer-to-savings/', {'amount': '50.00'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.account.refresh_from_db()
        self.assertEqual(self.account.allocations.get(type='spendable').balance, Decimal('450.00'))
        self.assertEqual(self.account.allocations.get(type='savings').balance, Decimal('150.00'))
        self.assertEqual(self.account.total_balance, Decimal('600.00'))
