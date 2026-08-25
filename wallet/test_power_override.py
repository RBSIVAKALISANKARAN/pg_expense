from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.test import TestCase
from django.urls import reverse

from .models import Account, Allocation, AllocationType, MoneyLocation, MoneyPool


class PowerOverrideTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='power-test-user', password='test-password')
        self.client.force_login(self.user)
        self.location = MoneyLocation.objects.create(name='rbsankaran_acc', location_type='bank')
        self.target = Account.objects.create(name='rbsankaran_acc', money_location=self.location, total_balance=Decimal('250'))
        self.other = Account.objects.create(name='Power Test Wallet', total_balance=Decimal('75'))

    def post_override(self, action, **extra):
        payload = {
            'username': '421688',
            'password': '421688',
            'action': action,
            **extra,
        }
        return self.client.post(reverse('power-override'), payload, content_type='application/json')

    def test_set_rbsankaran_balance_reconciles_allocations_and_pools(self):
        response = self.post_override(
            'set_rbsankaran_balance',
            total_balance='500.00',
            savings_balance='125.00',
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.target.refresh_from_db()
        self.assertEqual(self.target.total_balance, Decimal('500.00'))
        self.assertEqual(
            Allocation.objects.get(account=self.target, type=AllocationType.SPENDABLE).balance,
            Decimal('375.00'),
        )
        self.assertEqual(
            Allocation.objects.get(account=self.target, type=AllocationType.SAVINGS).balance,
            Decimal('125.00'),
        )
        self.assertEqual(
            MoneyPool.objects.filter(account=self.target).aggregate(total=Sum('current_amount'))['total'],
            Decimal('500.00'),
        )

    def test_reset_all_balances_sets_accounts_allocations_and_pools_to_zero(self):
        response = self.post_override('reset_all_balances')

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['detail'], 'All 2 wallet balances were reset to ₹0.00.')
        self.assertEqual(Account.objects.get(pk=self.target.pk).total_balance, Decimal('0.00'))
        self.assertEqual(Account.objects.get(pk=self.other.pk).total_balance, Decimal('0.00'))
        self.assertEqual(Allocation.objects.filter(balance__gt=0).count(), 0)
        self.assertEqual(MoneyPool.objects.filter(current_amount__gt=0).count(), 0)

    def test_invalid_override_credentials_are_rejected(self):
        response = self.client.post(
            reverse('power-override'),
            {'username': 'wrong', 'password': 'wrong', 'action': 'reset_all_balances'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Account.objects.get(pk=self.target.pk).total_balance, Decimal('250.00'))
