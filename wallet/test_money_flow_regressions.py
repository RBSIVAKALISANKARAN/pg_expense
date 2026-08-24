from decimal import Decimal

from django.db.models import Sum
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Account, Allocation, Category, MoneyPool, Owner, Transaction


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
        self.travel.refresh_from_db()
        self.assertEqual(self.travel.total_balance, Decimal('300'))
        self.assertEqual(self.upi.total_balance + self.travel.total_balance, Decimal('1000'))

    def test_primary_wallet_deposit_repairs_stale_pool_context(self):
        account = Account.objects.get(name='rbsankaran_acc')
        pool = MoneyPool.objects.get(account=account, allocation_type='spendable')
        appa = Owner.objects.get(name='Appa')
        pool.owner = appa
        pool.save(update_fields=['owner', 'updated_at'])

        response = self.client.post(
            f'/api/accounts/{account.id}/deposit/',
            {'amount': '500'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        account.refresh_from_db()
        pool.refresh_from_db()
        self.assertEqual(account.total_balance, Decimal('500'))
        self.assertEqual(pool.current_amount, Decimal('500'))
        self.assertEqual(pool.owner.name, 'Me')

    def test_primary_wallet_deposit_repairs_legacy_account_only_balance(self):
        account = Account.objects.get(name='rbsankaran_acc')
        account.total_balance = Decimal('484')
        account.save(update_fields=['total_balance', 'updated_at'])
        Allocation.objects.filter(account=account).update(balance=Decimal('0'))
        MoneyPool.objects.filter(account=account).update(current_amount=Decimal('0'))

        response = self.client.post(
            f'/api/accounts/{account.id}/deposit/',
            {'amount': '16'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        account.refresh_from_db()
        self.assertEqual(account.total_balance, Decimal('500'))
        self.assertEqual(account.allocations.get(type='spendable').balance, Decimal('500'))
        self.assertEqual(account.allocations.get(type='savings').balance, Decimal('0'))
        self.assertEqual(
            account.money_pools.filter(allocation_type='spendable').aggregate(total=Sum('current_amount'))['total'],
            Decimal('500'),
        )

    def test_standard_allocation_transfer_keeps_total_balance(self):
        account = Account.objects.get(name='rbsankaran_acc')
        response = self.client.post(
            f'/api/accounts/{account.id}/deposit/',
            {'amount': '1000'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.post(
            f'/api/accounts/{account.id}/transfer-to-savings/',
            {'amount': '250'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        account.refresh_from_db()
        self.assertEqual(account.total_balance, Decimal('1000'))
        self.assertEqual(account.allocations.get(type='spendable').balance, Decimal('750'))
        self.assertEqual(account.allocations.get(type='savings').balance, Decimal('250'))
