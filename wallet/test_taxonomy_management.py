from django.test import TestCase
from rest_framework.test import APIClient

from .models import Category, FoodProfile, Item, SubCategory


class TaxonomyManagementTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.food = Category.objects.create(name='Food')
        self.main_meal = SubCategory.objects.create(category=self.food, name='Main Meal')
        self.beverage = SubCategory.objects.create(category=self.food, name='Beverage')
        self.dosa = Item.objects.create(category=self.food, subcategory=self.main_meal, name='Dosa')
        self.tea = Item.objects.create(category=self.food, subcategory=self.beverage, name='Tea')
        self.soap_category = Category.objects.create(name='Personal Care')
        self.soap = Item.objects.create(category=self.soap_category, name='Soap')

    def test_food_taxonomy_lists_fixed_dimensions_and_profiles(self):
        FoodProfile.objects.create(
            item=self.dosa,
            food_type='food',
            food_group='main_meal',
            health_classification='neutral',
            sugary='no',
        )
        response = self.client.get('/api/food-taxonomy/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['profiles'][0]['item_name'], 'Dosa')
        self.assertIn({'value': 'drink', 'label': 'Drink'}, response.data['choices']['food_type'])
        self.assertIn({'value': 'junk', 'label': 'Junk'}, response.data['choices']['health_classification'])

    def test_food_profile_is_upserted_from_category_page_api(self):
        payload = {
            'item': str(self.tea.id),
            'food_type': 'drink',
            'food_group': 'beverage',
            'health_classification': 'neutral',
            'sugary': 'yes',
        }
        first = self.client.post('/api/food-taxonomy/', payload, format='json')
        self.assertEqual(first.status_code, 201)
        self.assertEqual(FoodProfile.objects.get(item=self.tea).sugary, 'yes')

        payload['sugary'] = 'no'
        second = self.client.post('/api/food-taxonomy/', payload, format='json')
        self.assertEqual(second.status_code, 200)
        profile = FoodProfile.objects.get(item=self.tea)
        self.assertEqual(profile.sugary, 'no')
        self.assertEqual(FoodProfile.objects.filter(item=self.tea).count(), 1)

    def test_non_food_item_cannot_receive_food_profile(self):
        response = self.client.post('/api/food-taxonomy/', {
            'item': str(self.soap.id),
            'food_type': 'food',
            'food_group': 'other',
            'health_classification': 'unknown',
            'sugary': 'unknown',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(FoodProfile.objects.filter(item=self.soap).exists())
