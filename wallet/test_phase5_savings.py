from decimal import Decimal
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Account, Allocation, AllocationType, MoneyLocation, Owner, Transaction, TransactionType


class Phase5SavingsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='phase5-user', password='test-password')
        self.client.force_login(self.user)
        self.owner = Owner.objects.create(name='Phase5 Owner')
        self.location = MoneyLocation.objects.create(name='Phase5 Bank', location_type='bank')
        self.account = Account.objects.create(name='Phase5 Wallet', money_location=self.location, currency='INR', total_balance=Decimal('1000'))
        self.spendable = Allocation.objects.create(account=self.account, type=AllocationType.SPENDABLE, balance=Decimal('700'))
        self.savings = Allocation.objects.create(account=self.account, type=AllocationType.SAVINGS, balance=Decimal('300'))
        now = timezone.now()
        Transaction.objects.create(account=self.account, owner=self.owner, money_location=self.location, allocation=self.savings,
                                   type=TransactionType.DEPOSIT, amount=Decimal('300'), occurred_at=now,
                                   metadata={'portion': 'savings'})
        Transaction.objects.create(account=self.account, owner=self.owner, money_location=self.location, allocation=self.savings,
                                   type=TransactionType.TRANSFER, amount=Decimal('100'), occurred_at=now + timedelta(minutes=1),
                                   metadata={'direction': 'to_savings'})
        Transaction.objects.create(account=self.account, owner=self.owner, money_location=self.location, allocation=self.spendable,
                                   type=TransactionType.TRANSFER, amount=Decimal('40'), occurred_at=now + timedelta(minutes=2),
                                   metadata={'direction': 'to_spendable'})

    def test_savings_overview_uses_transaction_movements_without_double_counting(self):
        response = self.client.get('/api/savings/analytics/')
        self.assertEqual(response.status_code, 200)
        overview = response.data['overview']
        self.assertEqual(overview['inflow'], '400.00')
        self.assertEqual(overview['outflow'], '40.00')
        self.assertEqual(overview['net_savings'], '360.00')
        self.assertEqual(overview['movement_count'], 3)

    def test_savings_period_filter(self):
        today = timezone.localdate().isoformat()
        response = self.client.get(f'/api/savings/analytics/?date_from={today}&date_to={today}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['overview']['net_savings'], '360.00')

    def test_savings_wallet_and_location_breakdowns(self):
        response = self.client.get('/api/savings/analytics/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['by_wallet'][0]['name'], 'Phase5 Wallet')
        self.assertEqual(response.data['by_wallet'][0]['net'], '360.00')
        self.assertEqual(response.data['by_location'][0]['name'], 'Phase5 Bank')

    def test_savings_page_requires_login(self):
        self.client.logout()
        response = self.client.get('/api/savings/analytics/')
        self.assertEqual(response.status_code, 401)

    def test_savings_page_is_available_to_authenticated_user(self):
        response = self.client.get('/api/savings/page/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Savings tracking')
