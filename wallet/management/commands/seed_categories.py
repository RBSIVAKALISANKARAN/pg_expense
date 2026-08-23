"""
Seeds Category / SubCategory / Item / FoodProfile master data from the
family expense-tracking design document (richtext_converted_to_markdown).

This is intentionally idempotent (get_or_create everywhere) so it is safe
to run repeatedly, including in CI or on an existing database.

Anything the document explicitly calls "typeable"/free text (soap brand,
shampoo brand, transport provider, food variant such as "Podi Dosa") is
NOT seeded as master data on purpose — those are meant to be captured on
the transaction via the free-text `variant` field, not forced into a
lookup table. Only the fixed hierarchy (category -> subcategory -> item)
and food attributes described in the doc are seeded here.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from wallet.models import Category, FoodGroup, FoodProfile, HealthClassification, Item, SubCategory, SugaryStatus

# category_name -> [subcategory names]
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

# (category, subcategory_or_None, item_name)
PLAIN_ITEMS = [
    # --- Food: Main Meal ---
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
    # --- Food: Bakery ---
    ('Food', 'Bakery', 'Cream Bun'),
    ('Food', 'Bakery', 'Jam Bun'),
    ('Food', 'Bakery', 'Normal Bun'),
    ('Food', 'Bakery', 'Puffs'),
    # --- Transport: Public Transport ---
    ('Transport', 'Public Transport', 'Bus'),
    ('Transport', 'Public Transport', 'Metro'),
    ('Transport', 'Public Transport', 'Train'),
    # --- Transport: Ride Hailing ---
    ('Transport', 'Ride Hailing', 'Rapido'),
    ('Transport', 'Ride Hailing', 'Uber'),
    ('Transport', 'Ride Hailing', 'Ola'),
    # --- Personal Care (no subcategory tier per doc) ---
    ('Personal Care', None, 'Soap - Bathing Soap'),
    ('Personal Care', None, 'Soap - Washing Soap'),
    ('Personal Care', None, 'Shampoo'),
]

# Food items with their attributes: (item_name, food_group, health, sugary)
FOOD_PROFILES = {
    'Idly': (FoodGroup.MAIN_MEAL, HealthClassification.HEALTHY, SugaryStatus.NO),
    'Dosa': (FoodGroup.MAIN_MEAL, HealthClassification.NEUTRAL, SugaryStatus.NO),
    'Poori': (FoodGroup.MAIN_MEAL, HealthClassification.NEUTRAL, SugaryStatus.NO),
    'Pongal': (FoodGroup.MAIN_MEAL, HealthClassification.NEUTRAL, SugaryStatus.NO),
    'Tomato Rice': (FoodGroup.MAIN_MEAL, HealthClassification.NEUTRAL, SugaryStatus.NO),
    'Lemon Rice': (FoodGroup.MAIN_MEAL, HealthClassification.NEUTRAL, SugaryStatus.NO),
    'Brinji': (FoodGroup.MAIN_MEAL, HealthClassification.NEUTRAL, SugaryStatus.NO),
    'Chapathi': (FoodGroup.MAIN_MEAL, HealthClassification.HEALTHY, SugaryStatus.NO),
    'Parotta': (FoodGroup.MAIN_MEAL, HealthClassification.JUNK, SugaryStatus.NO),
    'Fried Rice': (FoodGroup.MAIN_MEAL, HealthClassification.NEUTRAL, SugaryStatus.NO),
    'Cream Bun': (FoodGroup.BAKERY, HealthClassification.JUNK, SugaryStatus.YES),
    'Jam Bun': (FoodGroup.BAKERY, HealthClassification.JUNK, SugaryStatus.YES),
    'Normal Bun': (FoodGroup.BAKERY, HealthClassification.NEUTRAL, SugaryStatus.UNKNOWN),
    'Puffs': (FoodGroup.BAKERY, HealthClassification.JUNK, SugaryStatus.UNKNOWN),
}


class Command(BaseCommand):
    help = 'Seed Category/SubCategory/Item/FoodProfile master data from the design document.'

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
                    food_group, health, sugary = profile_attrs
                    _, was_created = FoodProfile.objects.get_or_create(
                        item=item,
                        defaults={
                            'food_group': food_group,
                            'health_classification': health,
                            'sugary': sugary,
                        },
                    )
                    created['food_profiles'] += int(was_created)

        self.stdout.write(self.style.SUCCESS(
            f"Seed complete. Created: {created['categories']} categories, "
            f"{created['subcategories']} subcategories, {created['items']} items, "
            f"{created['food_profiles']} food profiles."
        ))
