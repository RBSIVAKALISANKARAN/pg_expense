"""
Seeds Category / SubCategory / Item / FoodProfile master data from the
family expense-tracking design document.

This is intentionally idempotent so it is safe to run repeatedly, including
in CI or on an existing database.

Variants and brands remain transaction-level free text. The master data holds
only stable taxonomy and item-level food attributes.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from wallet.models import (
    Category,
    FoodGroup,
    FoodProfile,
    FoodType,
    HealthClassification,
    Item,
    SubCategory,
    SugaryStatus,
)

CATEGORY_SUBCATEGORIES = {
    'Food': ['Main Meal', 'Snack', 'Bakery', 'Fruit', 'Vegetable', 'Protein', 'Beverage'],
    'Transport': ['Public Transport', 'Ride Hailing', 'Auto', 'Fuel', 'Parking', 'Toll'],
    'Personal Care': [],
    'Household / Cleaning': [],
    'Education / Stationery': [],
    'Medical': [],
    'Religious / Pooja': [],
    'Bank Charges': [],
    'Miscellaneous': ['Gift', 'Donation', 'Repair', 'Entertainment', 'Contribution', 'Fee', 'Fine', 'Other'],
}

PLAIN_ITEMS = [
    # Food: main meals
    ('Food', 'Main Meal', 'Idly'),
    ('Food', 'Main Meal', 'Dosa'),
    ('Food', 'Main Meal', 'Poori'),
    ('Food', 'Main Meal', 'Pongal'),
    ('Food', 'Main Meal', 'Tomato Rice'),
    ('Food', 'Main Meal', 'Lemon Rice'),
    ('Food', 'Main Meal', 'Brinji'),
    ('Food', 'Main Meal', 'Chapathi'),
    ('Food', 'Main Meal', 'Parotta'),
    ('Food', 'Main Meal', 'Fried Rice'),
    # Food: bakery / snacks
    ('Food', 'Bakery', 'Cream Bun'),
    ('Food', 'Bakery', 'Jam Bun'),
    ('Food', 'Bakery', 'Normal Bun'),
    ('Food', 'Bakery', 'Puffs'),
    ('Food', 'Snack', 'Biscuits'),
    # Food: fruit / vegetable / protein
    ('Food', 'Fruit', 'Banana'),
    ('Food', 'Vegetable', 'Carrot'),
    ('Food', 'Protein', 'Egg'),
    # Food: drinks
    ('Food', 'Beverage', 'Tea'),
    ('Food', 'Beverage', 'Coffee'),
    ('Food', 'Beverage', 'Boost'),
    ('Food', 'Beverage', 'Cool Drink'),
    # Transport
    ('Transport', 'Public Transport', 'Bus'),
    ('Transport', 'Public Transport', 'Metro'),
    ('Transport', 'Public Transport', 'Train'),
    ('Transport', 'Ride Hailing', 'Rapido'),
    ('Transport', 'Ride Hailing', 'Uber'),
    ('Transport', 'Ride Hailing', 'Ola'),
    # Personal Care (no subcategory tier)
    ('Personal Care', None, 'Soap - Bathing Soap'),
    ('Personal Care', None, 'Soap - Washing Soap'),
    ('Personal Care', None, 'Shampoo'),
]

# item_name -> (food_type, food_group, health, sugary)
FOOD_PROFILES = {
    'Idly': (FoodType.FOOD, FoodGroup.MAIN_MEAL, HealthClassification.HEALTHY, SugaryStatus.NO),
    'Dosa': (FoodType.FOOD, FoodGroup.MAIN_MEAL, HealthClassification.NEUTRAL, SugaryStatus.NO),
    'Poori': (FoodType.FOOD, FoodGroup.MAIN_MEAL, HealthClassification.NEUTRAL, SugaryStatus.NO),
    'Pongal': (FoodType.FOOD, FoodGroup.MAIN_MEAL, HealthClassification.NEUTRAL, SugaryStatus.NO),
    'Tomato Rice': (FoodType.FOOD, FoodGroup.MAIN_MEAL, HealthClassification.NEUTRAL, SugaryStatus.NO),
    'Lemon Rice': (FoodType.FOOD, FoodGroup.MAIN_MEAL, HealthClassification.NEUTRAL, SugaryStatus.NO),
    'Brinji': (FoodType.FOOD, FoodGroup.MAIN_MEAL, HealthClassification.NEUTRAL, SugaryStatus.NO),
    'Chapathi': (FoodType.FOOD, FoodGroup.MAIN_MEAL, HealthClassification.HEALTHY, SugaryStatus.NO),
    'Parotta': (FoodType.FOOD, FoodGroup.MAIN_MEAL, HealthClassification.JUNK, SugaryStatus.NO),
    'Fried Rice': (FoodType.FOOD, FoodGroup.MAIN_MEAL, HealthClassification.NEUTRAL, SugaryStatus.NO),
    'Cream Bun': (FoodType.FOOD, FoodGroup.BAKERY, HealthClassification.JUNK, SugaryStatus.YES),
    'Jam Bun': (FoodType.FOOD, FoodGroup.BAKERY, HealthClassification.JUNK, SugaryStatus.YES),
    'Normal Bun': (FoodType.FOOD, FoodGroup.BAKERY, HealthClassification.NEUTRAL, SugaryStatus.UNKNOWN),
    'Puffs': (FoodType.FOOD, FoodGroup.BAKERY, HealthClassification.JUNK, SugaryStatus.UNKNOWN),
    'Biscuits': (FoodType.FOOD, FoodGroup.SNACK, HealthClassification.JUNK, SugaryStatus.UNKNOWN),
    'Banana': (FoodType.FOOD, FoodGroup.FRUIT, HealthClassification.HEALTHY, SugaryStatus.NO),
    'Carrot': (FoodType.FOOD, FoodGroup.VEGETABLE, HealthClassification.HEALTHY, SugaryStatus.NO),
    'Egg': (FoodType.FOOD, FoodGroup.PROTEIN, HealthClassification.HEALTHY, SugaryStatus.NO),
    'Tea': (FoodType.DRINK, FoodGroup.BEVERAGE, HealthClassification.NEUTRAL, SugaryStatus.UNKNOWN),
    'Coffee': (FoodType.DRINK, FoodGroup.BEVERAGE, HealthClassification.NEUTRAL, SugaryStatus.UNKNOWN),
    'Boost': (FoodType.DRINK, FoodGroup.BEVERAGE, HealthClassification.NEUTRAL, SugaryStatus.YES),
    'Cool Drink': (FoodType.DRINK, FoodGroup.BEVERAGE, HealthClassification.JUNK, SugaryStatus.YES),
}


class Command(BaseCommand):
    help = 'Seed Category/SubCategory/Item/FoodProfile master data.'

    def handle(self, *args, **options):
        created = {'categories': 0, 'subcategories': 0, 'items': 0, 'food_profiles': 0}

        with transaction.atomic():
            category_objs = {}
            subcategory_objs = {}

            for category_name, subcategory_names in CATEGORY_SUBCATEGORIES.items():
                category, was_created = Category.objects.get_or_create(name=category_name)
                category_objs[category_name] = category
                created['categories'] += int(was_created)

                for subcategory_name in subcategory_names:
                    subcategory, was_created = SubCategory.objects.get_or_create(
                        category=category, name=subcategory_name,
                    )
                    subcategory_objs[(category_name, subcategory_name)] = subcategory
                    created['subcategories'] += int(was_created)

            for category_name, subcategory_name, item_name in PLAIN_ITEMS:
                category = category_objs[category_name]
                subcategory = subcategory_objs.get((category_name, subcategory_name)) if subcategory_name else None
                item, was_created = Item.objects.get_or_create(
                    category=category,
                    subcategory=subcategory,
                    name=item_name,
                    defaults={'is_custom': False},
                )
                created['items'] += int(was_created)

                profile_attrs = FOOD_PROFILES.get(item_name)
                if profile_attrs:
                    food_type, food_group, health, sugary = profile_attrs
                    _, was_created = FoodProfile.objects.update_or_create(
                        item=item,
                        defaults={
                            'food_type': food_type,
                            'food_group': food_group,
                            'health_classification': health,
                            'sugary': sugary,
                        },
                    )
                    created['food_profiles'] += int(was_created)

        self.stdout.write(self.style.SUCCESS(
            f"Seed complete. Created/updated: {created['categories']} categories, "
            f"{created['subcategories']} subcategories, {created['items']} items, "
            f"{created['food_profiles']} food profiles."
        ))
