from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Account, Allocation, AllocationType, Category, FoodEvent, FoodEventItem, FoodProfile, Item, MoneyLocation, MoneyPool, Owner, SubCategory, Transaction


class WalletTests(TestCase):
    def setUp(self):
        self.acc = Account.objects.create(name='TestAccount')
        Allocation.objects.get_or_create(account=self.acc, type=AllocationType.SPENDABLE)
        Allocation.objects.get_or_create(account=self.acc, type=AllocationType.SAVINGS)

    def test_deposit_with_savings_allocation(self):
        url = reverse('account-deposit', args=[self.acc.id])
        resp = self.client.post(url, {'amount': '1000', 'allocate_to_savings': '300', 'note': 'initial'}, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['total_balance'], '1000.00')
        allocs = {a['type']: Decimal(a['balance']) for a in data['allocations']}
        self.assertEqual(allocs['spendable'], Decimal('700.00'))
        self.assertEqual(allocs['savings'], Decimal('300.00'))

    def test_expense_from_spendable(self):
        self.client.post(reverse('account-deposit', args=[self.acc.id]), {'amount': '500'}, content_type='application/json')
        resp = self.client.post(reverse('account-expense', args=[self.acc.id]), {'amount': '200', 'allocation': 'spendable', 'merchant': 'Cafe'}, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['total_balance'], '300.00')

    def test_expense_persists_category_and_food_items(self):
        self.client.post(reverse('account-deposit', args=[self.acc.id]), {'amount': '500'}, content_type='application/json')

        category = Category.objects.create(name='Food')
        subcategory = SubCategory.objects.create(category=category, name='Restaurant')
        item = Item.objects.create(category=category, subcategory=subcategory, name='Coffee')

        resp = self.client.post(
            reverse('account-expense', args=[self.acc.id]),
            {'amount': '100', 'allocation': 'spendable', 'category': str(category.id), 'subcategory': str(subcategory.id), 'item': str(item.id), 'merchant': 'Cafe'},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        tx = Transaction.objects.get(account=self.acc, type='expense')
        self.assertEqual(tx.category_id, category.id)
        self.assertEqual(tx.subcategory_id, subcategory.id)
        self.assertEqual(tx.item_id, item.id)

    def test_transfer_to_savings(self):
        self.client.post(reverse('account-deposit', args=[self.acc.id]), {'amount': '500'}, content_type='application/json')
        resp = self.client.post(reverse('account-transfer-to-savings', args=[self.acc.id]), {'amount': '100'}, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['total_balance'], '500.00')

    def test_transfer_to_spendable(self):
        self.client.post(reverse('account-deposit', args=[self.acc.id]), {'amount': '500', 'allocate_to_savings': '200'}, content_type='application/json')
        resp = self.client.post(reverse('account-transfer-to-spendable', args=[self.acc.id]), {'amount': '100'}, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['total_balance'], '500.00')

    def test_default_owner_and_location_are_recorded_on_transaction(self):
        owner = Owner.objects.get(name='Me')
        location = MoneyLocation.objects.get(name='rbsankaran_acc')
        self.client.post(
            reverse('account-deposit', args=[self.acc.id]),
            {'amount': '1000', 'owner': owner.id, 'money_location': location.id, 'note': 'salary'},
            content_type='application/json',
        )
        tx = Transaction.objects.filter(account=self.acc).latest('created_at')
        self.assertEqual(tx.owner_id, owner.id)
        self.assertEqual(tx.money_location_id, location.id)
        self.assertIsNotNone(tx.source_pool)

    def test_money_pools_track_allocation_totals(self):
        owner = Owner.objects.get(name='Me')
        location = MoneyLocation.objects.get(name='rbsankaran_acc')

        self.client.post(
            reverse('account-deposit', args=[self.acc.id]),
            {'amount': '1000', 'allocate_to_savings': '300', 'owner': owner.id, 'money_location': location.id},
            content_type='application/json',
        )

        spendable_pool = MoneyPool.objects.get(account=self.acc, owner=owner, location=location, allocation_type=AllocationType.SPENDABLE)
        savings_pool = MoneyPool.objects.get(account=self.acc, owner=owner, location=location, allocation_type=AllocationType.SAVINGS)
        self.assertEqual(spendable_pool.current_amount, Decimal('700.00'))
        self.assertEqual(savings_pool.current_amount, Decimal('300.00'))

        self.client.post(
            reverse('account-transfer-to-savings', args=[self.acc.id]),
            {'amount': '100'},
            content_type='application/json',
        )

        spendable_pool.refresh_from_db()
        savings_pool.refresh_from_db()
        self.assertEqual(spendable_pool.current_amount, Decimal('600.00'))
        self.assertEqual(savings_pool.current_amount, Decimal('400.00'))

    def test_transfer_to_savings_and_back(self):
        self.client.post(reverse('account-deposit', args=[self.acc.id]), {'amount': '1000'}, content_type='application/json')
        resp = self.client.post(reverse('account-transfer-to-savings', args=[self.acc.id]), {'amount': '400'}, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        allocs = {a['type']: Decimal(a['balance']) for a in data['allocations']}
        self.assertEqual(allocs['spendable'], Decimal('600.00'))
        self.assertEqual(allocs['savings'], Decimal('400.00'))
