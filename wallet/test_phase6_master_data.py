from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Account, Category, Item, MoneyLocation, Owner, SubCategory


class Phase6MasterDataTests(TestCase):
    def json(self, response):
        self.assertTrue(response.headers.get('Content-Type', '').startswith('application/json'), response.content)
        return response.json()

    def test_accounts_can_be_created_and_updated(self):
        location = MoneyLocation.objects.create(name='Phase6 Bank', location_type='bank')
        response = self.client.post(reverse('master-accounts'), {
            'name': 'Phase6 Account', 'currency': 'INR', 'money_location': str(location.id)
        }, content_type='application/json')
        self.assertEqual(response.status_code, 201, response.content)
        account = Account.objects.get(name='Phase6 Account')
        response = self.client.post(reverse('master-account-detail', args=[account.id]), {
            'name': 'Phase6 Account Updated', 'currency': 'INR'
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        account.refresh_from_db()
        self.assertEqual(account.name, 'Phase6 Account Updated')

    def test_non_zero_account_cannot_be_archived(self):
        account = Account.objects.create(name='Phase6 Nonzero', total_balance=Decimal('100'))
        response = self.client.post(reverse('master-account-status', args=[account.id]), {'active': False}, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        account.refresh_from_db()
        self.assertTrue(account.active)

    def test_zero_account_can_be_archived_and_reactivated(self):
        account = Account.objects.create(name='Phase6 Zero')
        response = self.client.post(reverse('master-account-status', args=[account.id]), {'active': False}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        account.refresh_from_db()
        self.assertFalse(account.active)
        response = self.client.post(reverse('master-account-status', args=[account.id]), {'active': True}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        account.refresh_from_db()
        self.assertTrue(account.active)

    def test_category_archive_cascades_to_subcategories_and_items(self):
        category = Category.objects.create(name='Phase6 Category')
        sub = SubCategory.objects.create(category=category, name='Phase6 Sub')
        item = Item.objects.create(category=category, subcategory=sub, name='Phase6 Item')
        response = self.client.post(reverse('master-category-status', args=[category.id]), {'active': False}, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        category.refresh_from_db(); sub.refresh_from_db(); item.refresh_from_db()
        self.assertFalse(category.active)
        self.assertFalse(sub.active)
        self.assertFalse(item.active)

    def test_subcategory_archive_cascades_to_items(self):
        category = Category.objects.create(name='Phase6 Category 2')
        sub = SubCategory.objects.create(category=category, name='Phase6 Sub 2')
        item = Item.objects.create(category=category, subcategory=sub, name='Phase6 Item 2')
        response = self.client.post(reverse('master-subcategory-status', args=[sub.id]), {'active': False}, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        item.refresh_from_db()
        self.assertFalse(item.active)

    def test_master_hierarchy_rejects_inactive_parent(self):
        category = Category.objects.create(name='Inactive Parent', active=False)
        response = self.client.post(reverse('master-subcategories'), {'category': str(category.id), 'name': 'Blocked'}, content_type='application/json')
        self.assertEqual(response.status_code, 404)

    def test_duplicate_owner_is_rejected(self):
        Owner.objects.create(name='Phase6 Owner')
        response = self.client.post(reverse('master-owners'), {'name': 'Phase6 Owner'}, content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_owner_can_be_archived_and_reactivated(self):
        owner = Owner.objects.create(name='Phase6 Owner 2')
        response = self.client.post(reverse('master-owner-status', args=[owner.id]), {'active': False}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        owner.refresh_from_db(); self.assertFalse(owner.active)
        response = self.client.post(reverse('master-owner-status', args=[owner.id]), {'active': True}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        owner.refresh_from_db(); self.assertTrue(owner.active)

    def test_money_location_used_by_active_account_cannot_be_archived(self):
        location = MoneyLocation.objects.create(name='Phase6 Used Location', location_type='bank')
        Account.objects.create(name='Phase6 Location Account', money_location=location)
        response = self.client.post(reverse('master-location-status', args=[location.id]), {'active': False}, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        location.refresh_from_db(); self.assertTrue(location.active)

    def test_configuration_rejects_inactive_defaults(self):
        owner = Owner.objects.create(name='Phase6 Inactive Owner', active=False)
        response = self.client.post(reverse('master-config'), {'default_owner': owner.name}, content_type='application/json')
        self.assertEqual(response.status_code, 400, response.content)

    def test_configuration_accepts_active_defaults(self):
        owner = Owner.objects.create(name='Phase6 Active Owner')
        location = MoneyLocation.objects.create(name='Phase6 Active Location', location_type='bank')
        response = self.client.post(reverse('master-config'), {
            'default_owner': owner.name, 'default_money_location': location.name,
            'default_allocation': 'savings'
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        data = self.json(response)
        self.assertEqual(data['default_owner'], owner.name)
        self.assertEqual(data['default_money_location'], location.name)
        self.assertEqual(data['default_allocation'], 'savings')

    def test_master_data_page_is_available(self):
        response = self.client.get(reverse('master-data-page'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Master Data & Configuration')
