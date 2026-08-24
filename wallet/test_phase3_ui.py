from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Account, Allocation, AppSetting


class Phase3SettingsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='phase3', password='phase3-pass')
        self.client = APIClient()
        self.client.login(username='phase3', password='phase3-pass')

    def test_settings_are_persistent(self):
        response = self.client.post('/api/settings/', {
            'app_name': 'PG Expense Test',
            'currency_default': 'INR',
            'timezone': 'Asia/Kolkata',
            'default_allocation': 'savings',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AppSetting.objects.get(key='app_name').value, 'PG Expense Test')
        fresh = self.client.get('/api/settings/')
        self.assertEqual(fresh.data['app_name'], 'PG Expense Test')
        self.assertEqual(fresh.data['default_allocation'], 'savings')

    def test_invalid_default_allocation_is_rejected(self):
        response = self.client.post('/api/settings/', {
            'default_allocation': 'invalid',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_settings_page_is_authenticated(self):
        self.client.logout()
        response = self.client.get('/api/settings/page/')
        self.assertEqual(response.status_code, 302)


class Phase3SavingsUiContractTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='phase3-savings', password='phase3-pass')
        self.client = APIClient()
        self.client.login(username='phase3-savings', password='phase3-pass')
        self.account = Account.objects.create(name='Phase 3 Wallet', currency='INR')
        Allocation.objects.create(account=self.account, type='spendable', balance=Decimal('500.00'))
        Allocation.objects.create(account=self.account, type='savings', balance=Decimal('100.00'))
        self.account.total_balance = Decimal('600.00')
        self.account.save(update_fields=['total_balance'])

    def test_settings_and_savings_routes_exist(self):
        self.assertEqual(self.client.get('/api/settings/').status_code, 200)
        self.assertEqual(self.client.post(f'/api/accounts/{self.account.id}/transfer-to-savings/', {'amount': '50.00'}).status_code, 200)
        self.account.refresh_from_db()
        self.assertEqual(self.account.allocations.get(type='spendable').balance, Decimal('450.00'))
        self.assertEqual(self.account.allocations.get(type='savings').balance, Decimal('150.00'))
