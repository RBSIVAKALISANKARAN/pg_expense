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
            {
                'amount': '150',
                'allocation': 'spendable',
                'category': category.id,
                'subcategory': subcategory.id,
                'item': item.id,
                'variant': 'Filter Coffee',
                'meal': 'breakfast',
                'food_items': [{'item': str(item.id), 'quantity': '2'}, {'custom_name': 'Toast', 'quantity': '1'}],
            },
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200, resp.content)

        tx = Transaction.objects.filter(account=self.acc, type='expense').latest('created_at')
        self.assertEqual(tx.category_id, category.id)
        self.assertEqual(tx.subcategory_id, subcategory.id)
        self.assertEqual(tx.item_id, item.id)
        self.assertEqual(tx.variant, 'Filter Coffee')
        self.assertEqual(tx.meal, 'breakfast')

        food_event = FoodEvent.objects.get(transaction=tx)
        self.assertEqual(food_event.meal, 'breakfast')
        items = list(FoodEventItem.objects.filter(event=food_event))
        self.assertEqual(len(items), 2)
        self.assertEqual({fi.custom_name for fi in items if fi.custom_name}, {'Toast'})

    def test_seed_categories_command_is_idempotent_and_builds_expected_tree(self):
        call_command('seed_categories')

        food = Category.objects.get(name='Food')
        transport = Category.objects.get(name='Transport')
        self.assertTrue(Category.objects.filter(name='Personal Care').exists())
        self.assertTrue(Category.objects.filter(name='Miscellaneous').exists())

        main_meal = SubCategory.objects.get(category=food, name='Main Meal')
        bakery = SubCategory.objects.get(category=food, name='Bakery')
        self.assertTrue(Item.objects.filter(category=food, subcategory=main_meal, name='Dosa').exists())
        self.assertTrue(Item.objects.filter(category=food, subcategory=main_meal, name='Idly').exists())
        self.assertTrue(Item.objects.filter(category=food, subcategory=bakery, name='Cream Bun').exists())

        ride_hailing = SubCategory.objects.get(category=transport, name='Ride Hailing')
        self.assertTrue(Item.objects.filter(category=transport, subcategory=ride_hailing, name='Uber').exists())

        soap = Item.objects.get(category=Category.objects.get(name='Personal Care'), name='Soap - Bathing Soap')
        self.assertIsNone(soap.subcategory)

        idly = Item.objects.get(category=food, subcategory=main_meal, name='Idly')
        profile = FoodProfile.objects.get(item=idly)
        self.assertEqual(profile.food_group, 'main_meal')

        # Running it again must not create duplicates.
        before_categories = Category.objects.count()
        before_items = Item.objects.count()
        call_command('seed_categories')
        self.assertEqual(Category.objects.count(), before_categories)
        self.assertEqual(Item.objects.count(), before_items)

    def test_expense_supports_typable_variant_without_master_data(self):
        # Per the design doc: soap brand, shampoo brand, transport provider,
        # and food variants (e.g. "Podi" Dosa) must be recordable as free
        # text without requiring a master-data row to exist first.
        call_command('seed_categories')
        self.client.post(reverse('account-deposit', args=[self.acc.id]), {'amount': '500'}, content_type='application/json')

        personal_care = Category.objects.get(name='Personal Care')
        soap = Item.objects.get(category=personal_care, name='Soap - Bathing Soap')

        resp = self.client.post(
            reverse('account-expense', args=[self.acc.id]),
            {
                'amount': '45',
                'allocation': 'spendable',
                'category': personal_care.id,
                'item': soap.id,
                'variant': 'Dove',
            },
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        tx = Transaction.objects.filter(account=self.acc, type='expense').latest('created_at')
        self.assertEqual(tx.item_id, soap.id)
        self.assertEqual(tx.variant, 'Dove')

    def test_expense_with_owner_and_location_does_not_crash_pool_checks(self):
        # Regression test: expense/transfer endpoints must accept an explicit
        # owner + money_location without raising a TypeError from the pool
        # helper functions (previously missing the `account` argument).
        owner = Owner.objects.create(name='Kid')
        location = MoneyLocation.objects.create(name='Piggy Bank')

        # Deposit into this specific owner/location's pool first (a fresh
        # account has no money_location yet, so this also binds it).
        resp = self.client.post(
            reverse('account-deposit', args=[self.acc.id]),
            {'amount': '1000', 'owner': owner.id, 'money_location': location.id},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200, resp.content)

        resp = self.client.post(
            reverse('account-expense', args=[self.acc.id]),
            {'amount': '50', 'allocation': 'spendable', 'owner': owner.id, 'money_location': location.id},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200, resp.content)

        resp = self.client.post(
            reverse('account-transfer-to-savings', args=[self.acc.id]),
            {'amount': '100', 'owner': owner.id, 'money_location': location.id},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200, resp.content)

        resp = self.client.post(
            reverse('account-transfer-to-spendable', args=[self.acc.id]),
            {'amount': '20', 'owner': owner.id, 'money_location': location.id},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_default_owner_and_location_are_recorded_on_transaction(self):
        owner = Owner.objects.create(name='Me')
        location = MoneyLocation.objects.create(name='TMB Bank')
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
        owner = Owner.objects.create(name='Me')
        location = MoneyLocation.objects.create(name='TMB Bank')

        self.client.post(
            reverse('account-deposit', args=[self.acc.id]),
            {'amount': '1000', 'allocate_to_savings': '300', 'owner': owner.id, 'money_location': location.id},
            content_type='application/json',
        )

        spendable_pool = MoneyPool.objects.get(owner=owner, location=location, allocation_type=AllocationType.SPENDABLE)
        savings_pool = MoneyPool.objects.get(owner=owner, location=location, allocation_type=AllocationType.SAVINGS)
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

        resp2 = self.client.post(reverse('account-transfer-to-spendable', args=[self.acc.id]), {'amount': '200'}, content_type='application/json')
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        allocs2 = {a['type']: Decimal(a['balance']) for a in data2['allocations']}
        self.assertEqual(allocs2['spendable'], Decimal('800.00'))
        self.assertEqual(allocs2['savings'], Decimal('200.00'))

    def test_summary_and_export(self):
        self.client.post(reverse('account-deposit', args=[self.acc.id]), {'amount': '1000'}, content_type='application/json')
        self.client.post(reverse('account-expense', args=[self.acc.id]), {'amount': '150', 'allocation': 'spendable', 'merchant': 'Groceries'}, content_type='application/json')

        summary_resp = self.client.get(reverse('account-summary', args=[self.acc.id]))
        self.assertEqual(summary_resp.status_code, 200)
        summary = summary_resp.json()
        self.assertEqual(summary['total_income'], '1000.00')
        self.assertEqual(summary['total_expenses'], '150.00')
        self.assertEqual(summary['net'], '850.00')

        export_resp = self.client.get(reverse('account-export-csv', args=[self.acc.id]))
        self.assertEqual(export_resp.status_code, 200)
        self.assertIn('expense', export_resp.content.decode('utf-8'))
        self.assertIn('deposit', export_resp.content.decode('utf-8'))

    def test_sql_playground_execute_and_schema(self):
        resp = self.client.post(
            reverse('sql-execute'),
            {'sql': "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name LIMIT 5;"},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload['status'], 'success')
        self.assertIn('rows', payload)
        self.assertGreaterEqual(payload['row_count'], 1)

        schema_resp = self.client.get(reverse('sql-schema'))
        self.assertEqual(schema_resp.status_code, 200)
        schema = schema_resp.json()
        self.assertIn('tables', schema)

        history_resp = self.client.get(reverse('sql-history'))
        self.assertEqual(history_resp.status_code, 200)
        self.assertTrue(len(history_resp.json()) >= 1)

        save_resp = self.client.post(
            reverse('sql-saved-queries'),
            {'name': 'Sample Query', 'sql': 'SELECT 1 AS answer;'},
            content_type='application/json',
        )
        self.assertEqual(save_resp.status_code, 201)
        self.assertEqual(save_resp.json()['name'], 'Sample Query')

        blocked_resp = self.client.post(
            reverse('sql-execute'),
            {'sql': "DROP TABLE wallet_account;"},
            content_type='application/json',
        )
        self.assertEqual(blocked_resp.status_code, 400)

    def test_category_subcategory_item_food_profile_and_settings_api(self):
        category_resp = self.client.post(reverse('categories-list-create'), {'name': 'Food', 'description': 'Meals'}, content_type='application/json')
        self.assertEqual(category_resp.status_code, 201)
        category_id = category_resp.json()['id']

        subcategory_resp = self.client.post(
            reverse('subcategories-list-create'),
            {'category': category_id, 'name': 'Lunch', 'description': 'Midday meals'},
            content_type='application/json',
        )
        self.assertEqual(subcategory_resp.status_code, 201)
        self.assertEqual(subcategory_resp.json()['name'], 'Lunch')

        item_resp = self.client.post(
            reverse('items-list-create'),
            {'category': category_id, 'subcategory': subcategory_resp.json()['id'], 'name': 'Meals', 'description': 'Food item', 'is_custom': True, 'food_group': 'snack', 'health_classification': 'junk', 'sugary': 'yes'},
            content_type='application/json',
        )
        self.assertEqual(item_resp.status_code, 201)
        self.assertEqual(item_resp.json()['name'], 'Meals')
        self.assertEqual(item_resp.json()['subcategory_name'], 'Lunch')

        profile_resp = self.client.get(reverse('food-profiles'))
        self.assertEqual(profile_resp.status_code, 200)
        self.assertTrue(any(item['item_name'] == 'Meals' for item in profile_resp.json()))

        self.client.post(reverse('account-deposit', args=[self.acc.id]), {'amount': '1000'}, content_type='application/json')
        expense_resp = self.client.post(
            reverse('account-expense', args=[self.acc.id]),
            {'amount': '50', 'allocation': 'spendable', 'merchant': 'Cafe', 'meal': 'breakfast'},
            content_type='application/json',
        )
        self.assertEqual(expense_resp.status_code, 200)
        tx = Transaction.objects.filter(account=self.acc).latest('created_at')
        self.assertEqual(tx.meal, 'breakfast')

        settings_resp = self.client.get(reverse('app-settings'))
        self.assertEqual(settings_resp.status_code, 200)
        self.assertEqual(settings_resp.json()['currency_default'], 'INR')

    def test_family_money_list_endpoints(self):
        Owner.objects.create(name='Me')
        Owner.objects.create(name='Appa')
        MoneyLocation.objects.create(name='TMB Bank')
        MoneyLocation.objects.create(name='Appa Cash')

        owners_resp = self.client.get(reverse('owners-list'))
        self.assertEqual(owners_resp.status_code, 200)
        self.assertTrue(any(item['name'] == 'Me' for item in owners_resp.json()))
        self.assertTrue(any(item['name'] == 'Appa' for item in owners_resp.json()))

        locations_resp = self.client.get(reverse('money-locations-list'))
        self.assertEqual(locations_resp.status_code, 200)
        self.assertTrue(any(item['name'] == 'TMB Bank' for item in locations_resp.json()))
        self.assertTrue(any(item['name'] == 'Appa Cash' for item in locations_resp.json()))
        self.assertTrue(any(item['name'] == 'Amma Cash' for item in locations_resp.json()))

        pools_resp = self.client.get(reverse('money-pools-list'))
        self.assertEqual(pools_resp.status_code, 200)

    def test_money_pool_identity_is_owner_location_allocation_type(self):
        owner = Owner.objects.create(name='Me')
        location = MoneyLocation.objects.create(name='TMB Bank')

        self.client.post(
            reverse('account-deposit', args=[self.acc.id]),
            {'amount': '1000', 'allocate_to_savings': '300', 'owner': owner.id, 'money_location': location.id},
            content_type='application/json',
        )

        self.assertTrue(MoneyPool.objects.filter(owner=owner, location=location, allocation_type=AllocationType.SPENDABLE).exists())
        self.assertTrue(MoneyPool.objects.filter(owner=owner, location=location, allocation_type=AllocationType.SAVINGS).exists())
        pools_resp = self.client.get(reverse('money-pools-list'))
        self.assertEqual(pools_resp.status_code, 200)
        pool = pools_resp.json()[0]
        self.assertIn('allocation_type', pool)
        self.assertNotIn('allocation', pool)

    def test_dashboard_page_renders_with_expense_taxonomy_ui(self):
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        # The cascading Category -> SubCategory -> Item -> Variant controls
        # and the custom-description fallback must be present in the markup.
        self.assertIn('expense-category', content)
        self.assertIn('expense-subcategory', content)
        self.assertIn('expense-item', content)
        self.assertIn('expense-variant', content)
        self.assertIn('expense-custom-description', content)
        self.assertIn('expense-meal', content)
        self.assertIn('loadExpenseTaxonomy', content)
        self.assertIn('wireExpenseCascades', content)

    def test_expense_api_end_to_end_with_full_taxonomy_payload(self):
        # Simulates exactly what the dashboard expense form now sends:
        # category + subcategory + item (all seeded master data) plus a
        # free-text variant, with no custom_description since a real item
        # was selected.
        call_command('seed_categories')
        self.client.post(reverse('account-deposit', args=[self.acc.id]), {'amount': '1000'}, content_type='application/json')

        food = Category.objects.get(name='Food')
        main_meal = SubCategory.objects.get(category=food, name='Main Meal')
        dosa = Item.objects.get(category=food, subcategory=main_meal, name='Dosa')

        resp = self.client.post(
            reverse('account-expense', args=[self.acc.id]),
            {
                'amount': '60',
                'allocation': 'spendable',
                'category': food.id,
                'subcategory': main_meal.id,
                'item': dosa.id,
                'variant': 'Podi',
                'meal': 'breakfast',
                'note': 'Corner shop',
            },
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200, resp.content)

        tx = Transaction.objects.filter(account=self.acc, type='expense').latest('created_at')
        self.assertEqual(tx.category_id, food.id)
        self.assertEqual(tx.subcategory_id, main_meal.id)
        self.assertEqual(tx.item_id, dosa.id)
        self.assertEqual(tx.variant, 'Podi')
        self.assertEqual(tx.meal, 'breakfast')
        self.assertEqual(tx.metadata.get('note'), 'Corner shop')

    def test_expense_api_end_to_end_with_custom_description_no_item(self):
        # Simulates the "Custom / Other" path: no item selected, category
        # optionally set, custom_description carries the free-text detail.
        call_command('seed_categories')
        self.client.post(reverse('account-deposit', args=[self.acc.id]), {'amount': '1000'}, content_type='application/json')

        misc = Category.objects.get(name='Miscellaneous')
        other = SubCategory.objects.get(category=misc, name='Other')

        resp = self.client.post(
            reverse('account-expense', args=[self.acc.id]),
            {
                'amount': '250',
                'allocation': 'spendable',
                'category': misc.id,
                'subcategory': other.id,
                'custom_description': 'College function contribution',
            },
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200, resp.content)

        tx = Transaction.objects.filter(account=self.acc, type='expense').latest('created_at')
        self.assertEqual(tx.category_id, misc.id)
        self.assertEqual(tx.subcategory_id, other.id)
        self.assertIsNone(tx.item_id)
        self.assertEqual(tx.metadata.get('custom_description'), 'College function contribution')
